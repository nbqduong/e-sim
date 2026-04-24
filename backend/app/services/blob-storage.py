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
from google.auth.transport.requests import Request

from .config import Settings

FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")
OBJECT_NAME_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")
GOOGLE_AUTH_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
GOOGLE_SIGNING_ALGORITHM = "GOOG4-RSA-SHA256"
MAX_SIGNED_URL_EXPIRATION_SECONDS = 604800
STORAGE_API_HOST = "storage.googleapis.com"


@dataclass(frozen=True)
class SigningIdentity:
    service_account_email: str
    sign_bytes: Callable[[bytes], bytes]


def normalize_archive_name(archive_name: str | None) -> str:
    candidate = (archive_name or "browser-files.zip").strip()
    candidate = FILENAME_SANITIZER.sub("-", candidate)
    candidate = candidate.strip(".-_") or "browser-files"

    if not candidate.lower().endswith(".zip"):
        candidate = f"{candidate}.zip"

    return candidate


def build_object_name(prefix: str, archive_name: str | None) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:10]
    normalized_prefix = prefix.strip("/ ")
    filename = normalize_archive_name(archive_name)

    if normalized_prefix:
        return f"{normalized_prefix}/{timestamp}-{suffix}-{filename}"

    return f"{timestamp}-{suffix}-{filename}"


def validate_signing_settings(settings: Settings) -> None:
    if not settings.gcs_bucket_name:
        raise ValueError("GCS_BUCKET_NAME is not configured.")
    if settings.max_upload_size_bytes <= 0:
        raise ValueError("PROJECT_METADATA_MAX_SIZE must be greater than 0.")
    if not 0 < settings.signed_url_expiration_seconds <= MAX_SIGNED_URL_EXPIRATION_SECONDS:
        raise ValueError(
            f"SIGNED_URL_EXPIRATION_SECONDS must be between 1 and "
            f"{MAX_SIGNED_URL_EXPIRATION_SECONDS}."
        )


def validate_download_object_name(settings: Settings, object_name: str) -> str:
    candidate = object_name.strip().lstrip("/")

    if not candidate:
        raise ValueError("object_name is required.")
    if OBJECT_NAME_CONTROL_CHARACTERS.search(candidate):
        raise ValueError("object_name contains unsupported control characters.")
    if candidate.endswith("/"):
        raise ValueError("object_name must identify a file.")
    if not candidate.lower().endswith(".zip"):
        raise ValueError("object_name must reference a .zip archive.")

    normalized_prefix = settings.gcs_upload_prefix.strip("/ ")
    if normalized_prefix and not candidate.startswith(f"{normalized_prefix}/"):
        raise ValueError(
            "object_name must be inside the configured upload prefix "
            f"`{normalized_prefix}/`."
        )

    return candidate


def validate_upload_content_length(settings: Settings, content_length: int) -> int:
    if content_length <= 0:
        raise ValueError("content_length must be greater than 0.")
    if content_length > settings.max_upload_size_bytes:
        raise ValueError(
            "Upload payload exceeds PROJECT_METADATA_MAX_SIZE. "
            f"Configured limit: {settings.max_upload_size_bytes} bytes."
        )

    return content_length


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


def create_signed_upload(
    settings: Settings,
    archive_name: str | None,
    content_type: str,
    content_length: int,
) -> dict[str, str | int]:
    validated_content_length = validate_upload_content_length(settings, content_length)
    object_name = build_object_name(settings.gcs_upload_prefix, archive_name)
    upload_url = create_signed_url(
        settings,
        method="PUT",
        object_name=object_name,
        headers={
            "content-length": str(validated_content_length),
            "content-type": content_type,
            "host": STORAGE_API_HOST,
        },
    )

    return {
        "bucketName": settings.gcs_bucket_name,
        "contentLength": validated_content_length,
        "contentType": content_type,
        "maxUploadSizeBytes": settings.max_upload_size_bytes,
        "method": "PUT",
        "objectName": object_name,
        "signedUrlExpirationSeconds": settings.signed_url_expiration_seconds,
        "storageUri": f"gs://{settings.gcs_bucket_name}/{object_name}",
        "uploadUrl": upload_url,
    }


def create_signed_download(settings: Settings, object_name: str) -> dict[str, str | int]:
    validated_object_name = validate_download_object_name(settings, object_name)
    download_url = create_signed_url(
        settings,
        method="GET",
        object_name=validated_object_name,
        headers={"host": STORAGE_API_HOST},
    )

    return {
        "bucketName": settings.gcs_bucket_name,
        "method": "GET",
        "objectName": validated_object_name,
        "signedUrlExpirationSeconds": settings.signed_url_expiration_seconds,
        "storageUri": f"gs://{settings.gcs_bucket_name}/{validated_object_name}",
        "downloadUrl": download_url,
    }
