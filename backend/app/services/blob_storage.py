from __future__ import annotations

import binascii
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import re
from typing import Callable
from urllib.parse import quote
import uuid

import google.auth
from google.auth import exceptions as auth_exceptions
from google.auth import iam
from google.auth.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession, Request
from requests import RequestException

from app.core.config import Settings

GOOGLE_AUTH_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
GOOGLE_SIGNING_ALGORITHM = "GOOG4-RSA-SHA256"
MAX_SIGNED_URL_EXPIRATION_SECONDS = 604800
STORAGE_API_HOST = "storage.googleapis.com"
PROJECT_OBJECT_SUFFIX = "content.zip"
ZIP_CONTENT_TYPE = "application/zip"
OBJECT_NAME_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")


@dataclass(frozen=True)
class SigningIdentity:
    service_account_email: str
    sign_bytes: Callable[[bytes], bytes]


def normalize_prefix(prefix: str) -> str:
    return prefix.strip("/ ")


def validate_signing_settings(settings: Settings) -> None:
    if not settings.gcs_bucket_name:
        raise ValueError("GCS_BUCKET_NAME is not configured.")
    if settings.max_upload_size_bytes <= 0:
        raise ValueError("PROJECT_CONTENT_MAX_UPLOAD_SIZE_BYTES must be greater than 0.")
    if not 0 < settings.signed_url_expiration_seconds <= MAX_SIGNED_URL_EXPIRATION_SECONDS:
        raise ValueError(
            f"SIGNED_URL_EXPIRATION_SECONDS must be between 1 and "
            f"{MAX_SIGNED_URL_EXPIRATION_SECONDS}."
        )


def validate_upload_content_length(settings: Settings, content_length: int) -> int:
    if content_length <= 0:
        raise ValueError("content_length must be greater than 0.")
    if content_length > settings.max_upload_size_bytes:
        raise ValueError(
            "Upload payload exceeds PROJECT_CONTENT_MAX_UPLOAD_SIZE_BYTES. "
            f"Configured limit: {settings.max_upload_size_bytes} bytes."
        )
    return content_length


def validate_content_type(content_type: str) -> str:
    candidate = content_type.strip()
    if candidate != ZIP_CONTENT_TYPE:
        raise ValueError(f"content_type must be `{ZIP_CONTENT_TYPE}`.")
    return candidate


def build_project_object_name(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> str:
    prefix = build_project_object_prefix(
        settings,
        user_id=user_id,
        project_id=project_id,
    )
    return f"{prefix}/{PROJECT_OBJECT_SUFFIX}"


def build_project_object_prefix(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> str:
    prefix = normalize_prefix(settings.gcs_upload_prefix)
    object_parts = [str(user_id), "project", str(project_id)]
    if prefix:
        object_parts.insert(0, prefix)
    return "/".join(object_parts)


def build_project_storage_uri(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> str:
    validate_signing_settings(settings)
    object_name = build_project_object_name(
        settings,
        user_id=user_id,
        project_id=project_id,
    )
    return f"gs://{settings.gcs_bucket_name}/{object_name}"


def extract_object_name_from_storage_uri(settings: Settings, storage_uri: str) -> str:
    validate_signing_settings(settings)
    bucket_name = settings.gcs_bucket_name
    prefix = f"gs://{bucket_name}/"
    if not storage_uri.startswith(prefix):
        raise ValueError("storage_uri must reference the configured GCS bucket.")

    object_name = storage_uri[len(prefix):].strip()
    normalized_prefix = normalize_prefix(settings.gcs_upload_prefix)
    if not object_name:
        raise ValueError("storage_uri must reference an object.")
    if OBJECT_NAME_CONTROL_CHARACTERS.search(object_name):
        raise ValueError("storage_uri contains unsupported control characters.")
    if normalized_prefix and not object_name.startswith(f"{normalized_prefix}/"):
        raise ValueError(
            "storage_uri must be inside the configured upload prefix "
            f"`{normalized_prefix}/`."
        )
    if not object_name.endswith(f"/{PROJECT_OBJECT_SUFFIX}"):
        raise ValueError(f"storage_uri must end with `{PROJECT_OBJECT_SUFFIX}`.")
    return object_name


@lru_cache
def get_auth_request() -> Request:
    return Request()


@lru_cache
def get_google_credentials() -> Credentials:
    credentials, _ = google.auth.default(scopes=GOOGLE_AUTH_SCOPES)
    return credentials


def get_signing_identity(settings: Settings) -> SigningIdentity:
    try:
        credentials = get_google_credentials()
    except auth_exceptions.DefaultCredentialsError as exc:
        raise ValueError(
            "No Google Cloud Application Default Credentials were found. "
            "Run `gcloud auth application-default login` on the host machine "
            "or provide impersonated ADC credentials."
        ) from exc

    configured_email = (settings.gcs_signing_service_account or "").strip() or None
    derived_email = (
        getattr(credentials, "signer_email", None)
        or getattr(credentials, "service_account_email", None)
    )
    signer_email = configured_email or derived_email

    if not signer_email:
        raise ValueError(
            "No signing service account is available. Set GCS_SIGNING_SERVICE_ACCOUNT "
            "or configure ADC with `gcloud auth application-default login "
            "--impersonate-service-account=SERVICE_ACCOUNT_EMAIL`."
        )

    sign_bytes = getattr(credentials, "sign_bytes", None)
    if callable(sign_bytes) and (
        not configured_email or configured_email == derived_email
    ):
        return SigningIdentity(service_account_email=signer_email, sign_bytes=sign_bytes)

    signer = iam.Signer(get_auth_request(), credentials, signer_email)
    return SigningIdentity(service_account_email=signer_email, sign_bytes=signer.sign)


def build_canonical_uri(bucket_name: str, object_name: str) -> str:
    return "/" + quote(f"{bucket_name}/{object_name}", safe="/~")


def build_canonical_headers(headers: dict[str, str]) -> tuple[str, str]:
    normalized_headers = OrderedDict(
        sorted(
            (
                key.strip().lower(),
                " ".join(str(value).strip().split()),
            )
            for key, value in headers.items()
        )
    )
    canonical_headers = "".join(
        f"{key}:{value}\n" for key, value in normalized_headers.items()
    )
    signed_headers = ";".join(normalized_headers.keys())
    return canonical_headers, signed_headers


def build_canonical_query_string(query_parameters: dict[str, str]) -> str:
    ordered_parameters = OrderedDict(sorted(query_parameters.items()))
    return "&".join(
        f"{quote(str(key), safe='')}={quote(str(value), safe='')}"
        for key, value in ordered_parameters.items()
    )


def format_google_auth_error(exc: Exception) -> str:
    return " ".join(str(exc).split())


def sign_string(identity: SigningIdentity, string_to_sign: str) -> str:
    try:
        raw_signature = identity.sign_bytes(string_to_sign.encode("utf-8"))
    except auth_exceptions.GoogleAuthError as exc:
        formatted_error = format_google_auth_error(exc)
        raise ValueError(
            "Unable to sign the URL with the current Google Cloud credentials. "
            f"Google returned: {formatted_error}. "
            "If you logged in with `gcloud auth application-default login "
            "--impersonate-service-account=...`, grant "
            "`roles/iam.serviceAccountTokenCreator` on the signing service account "
            "to the Google user or principal that ran that command."
        ) from exc

    return binascii.hexlify(raw_signature).decode("ascii")


def create_signed_url(
    settings: Settings,
    *,
    method: str,
    object_name: str,
    headers: dict[str, str],
) -> str:
    validate_signing_settings(settings)

    signing_identity = get_signing_identity(settings)
    now = datetime.now(timezone.utc)
    request_timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    credential_scope = f"{datestamp}/auto/storage/goog4_request"
    credential = f"{signing_identity.service_account_email}/{credential_scope}"

    canonical_uri = build_canonical_uri(settings.gcs_bucket_name, object_name)
    canonical_headers, signed_headers = build_canonical_headers(headers)
    canonical_query_string = build_canonical_query_string(
        {
            "X-Goog-Algorithm": GOOGLE_SIGNING_ALGORITHM,
            "X-Goog-Credential": credential,
            "X-Goog-Date": request_timestamp,
            "X-Goog-Expires": str(settings.signed_url_expiration_seconds),
            "X-Goog-SignedHeaders": signed_headers,
        }
    )
    canonical_request = "\n".join(
        [
            method,
            canonical_uri,
            canonical_query_string,
            canonical_headers,
            signed_headers,
            "UNSIGNED-PAYLOAD",
        ]
    )
    canonical_request_hash = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = "\n".join(
        [
            GOOGLE_SIGNING_ALGORITHM,
            request_timestamp,
            credential_scope,
            canonical_request_hash,
        ]
    )
    signature = sign_string(signing_identity, string_to_sign)
    return (
        f"https://{STORAGE_API_HOST}{canonical_uri}"
        f"?{canonical_query_string}&X-Goog-Signature={signature}"
    )


def create_signed_project_upload(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    content_type: str,
    content_length: int,
) -> dict[str, str | int]:
    validated_content_type = validate_content_type(content_type)
    validated_content_length = validate_upload_content_length(settings, content_length)
    object_name = build_project_object_name(
        settings,
        user_id=user_id,
        project_id=project_id,
    )
    upload_url = create_signed_url(
        settings,
        method="PUT",
        object_name=object_name,
        headers={
            "content-length": str(validated_content_length),
            "content-type": validated_content_type,
            "host": STORAGE_API_HOST,
        },
    )

    return {
        "bucket_name": settings.gcs_bucket_name or "",
        "content_length": validated_content_length,
        "content_type": validated_content_type,
        "max_upload_size_bytes": settings.max_upload_size_bytes,
        "method": "PUT",
        "object_name": object_name,
        "signed_url_expiration_seconds": settings.signed_url_expiration_seconds,
        "storage_uri": f"gs://{settings.gcs_bucket_name}/{object_name}",
        "upload_url": upload_url,
    }


def create_signed_project_download(
    settings: Settings,
    *,
    storage_uri: str,
) -> dict[str, str | int]:
    object_name = extract_object_name_from_storage_uri(settings, storage_uri)
    download_url = create_signed_url(
        settings,
        method="GET",
        object_name=object_name,
        headers={"host": STORAGE_API_HOST},
    )

    return {
        "bucket_name": settings.gcs_bucket_name or "",
        "method": "GET",
        "object_name": object_name,
        "signed_url_expiration_seconds": settings.signed_url_expiration_seconds,
        "storage_uri": f"gs://{settings.gcs_bucket_name}/{object_name}",
        "download_url": download_url,
    }


def delete_project_prefix(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    """Delete every object stored under a project's GCS prefix."""
    validate_signing_settings(settings)
    object_prefix = build_project_object_prefix(
        settings,
        user_id=user_id,
        project_id=project_id,
    ).rstrip("/") + "/"
    try:
        credentials = get_google_credentials()
    except auth_exceptions.DefaultCredentialsError as exc:
        raise ValueError(
            "No Google Cloud Application Default Credentials were found. "
            "Run `gcloud auth application-default login` on the host machine "
            "or provide service account credentials."
        ) from exc

    authed_session = AuthorizedSession(credentials)
    try:
        next_page_token: str | None = None
        bucket_name = quote(settings.gcs_bucket_name or "", safe="")

        while True:
            list_url = (
                f"https://{STORAGE_API_HOST}/storage/v1/b/{bucket_name}/o"
                f"?prefix={quote(object_prefix, safe='')}"
            )
            if next_page_token:
                list_url += f"&pageToken={quote(next_page_token, safe='')}"

            list_response = authed_session.get(list_url, timeout=30)
            if list_response.status_code != 200:
                raise ValueError(
                    "Unable to list project content in GCS. "
                    "Google Cloud Storage returned "
                    f"{list_response.status_code}: {list_response.text}"
                )

            payload = list_response.json()
            items = payload.get("items", [])
            for item in items:
                object_name = item.get("name")
                if not object_name:
                    continue
                delete_response = authed_session.delete(
                    f"https://{STORAGE_API_HOST}/storage/v1/b/{bucket_name}/o/"
                    f"{quote(object_name, safe='')}",
                    timeout=30,
                )
                if delete_response.status_code not in (204, 404):
                    raise ValueError(
                        "Unable to delete project content from GCS. "
                        "Google Cloud Storage returned "
                        f"{delete_response.status_code}: {delete_response.text}"
                    )

            next_page_token = payload.get("nextPageToken")
            if not next_page_token:
                break
    except (auth_exceptions.GoogleAuthError, RequestException) as exc:
        formatted_error = format_google_auth_error(exc)
        raise ValueError(
            "Unable to delete project storage from GCS. "
            f"Google Cloud Storage returned: {formatted_error}."
        ) from exc
    finally:
        authed_session.close()
