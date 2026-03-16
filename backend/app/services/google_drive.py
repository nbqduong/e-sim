from __future__ import annotations

import io
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.core.config import Settings
from app.schemas.auth import OAuthToken
from app.schemas.document import Document
from app.storage.token_store import TokenStore


class DriveAuthorizationError(RuntimeError):
    pass


class DriveExportError(RuntimeError):
    pass


DEFAULT_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]


class GoogleDriveService:
    def __init__(self, *, settings: Settings, token_store: TokenStore) -> None:
        self._settings = settings
        self._token_store = token_store

    def export_document(self, *, user_id: str, document: Document) -> dict[str, Any]:
        token = self._token_store.get(user_id)
        if token is None:
            raise DriveAuthorizationError("No Google credentials found for the current user")

        credentials = self._build_credentials(token)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            refreshed = token.update_from_credentials(credentials)
            self._token_store.save(refreshed)

        service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        # Ensure _ESimulate folder exists
        parent_id = self._settings.google_drive_parent_id
        folder_id = self._get_or_create_folder(service, "_ESimulate", parent_id)

        file_metadata: dict[str, Any] = {
            "name": f"{document.title}.txt",
            "mimeType": "text/plain",
        }

        media_body = MediaIoBaseUpload(
            io.BytesIO(document.content.encode("utf-8")),
            mimetype="text/plain",
            resumable=False,
        )

        try:
            if document.drive_file_id:
                file = (
                    service.files()
                    .update(
                        fileId=document.drive_file_id,
                        media_body=media_body,
                        body=file_metadata,
                        fields="id, webViewLink",
                    )
                    .execute()
                )
            else:
                file_metadata["parents"] = [folder_id]
                file = (
                    service.files()
                    .create(body=file_metadata, media_body=media_body, fields="id, webViewLink")
                    .execute()
                )
        except HttpError as exc:  # pragma: no cover - relies on network
            raise DriveExportError("Failed to upload document to Google Drive") from exc

        return file

    def list_documents(self, *, user_id: str) -> list[dict[str, Any]]:
        token = self._token_store.get(user_id)
        if token is None:
            raise DriveAuthorizationError("No Google credentials found for the current user")

        credentials = self._build_credentials(token)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            refreshed = token.update_from_credentials(credentials)
            self._token_store.save(refreshed)

        service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        # Get folder ID
        parent_id = self._settings.google_drive_parent_id
        folder_id = self._get_or_create_folder(service, "_ESimulate", parent_id)

        # List files in the folder
        query = f"'{folder_id}' in parents and trashed = false"
        try:
            results = (
                service.files()
                .list(q=query, spaces="drive", fields="files(id, name, webViewLink, modifiedTime)")
                .execute()
            )
            return results.get("files", [])
        except HttpError as exc:
            raise DriveExportError("Failed to list documents from Google Drive") from exc

    def get_document_content(self, *, user_id: str, drive_file_id: str) -> str:
        """Download the text content of a file from Google Drive."""
        token = self._token_store.get(user_id)
        if token is None:
            raise DriveAuthorizationError("No Google credentials found for the current user")

        credentials = self._build_credentials(token)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            refreshed = token.update_from_credentials(credentials)
            self._token_store.save(refreshed)

        service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        try:
            request = service.files().get_media(fileId=drive_file_id)
            content_bytes = request.execute()
            if isinstance(content_bytes, bytes):
                return content_bytes.decode("utf-8")
            return str(content_bytes)
        except HttpError as exc:
            raise DriveExportError("Failed to download document content from Google Drive") from exc

    def delete_document(self, *, user_id: str, drive_file_id: str) -> None:
        """Trash a file on Google Drive."""
        token = self._token_store.get(user_id)
        if token is None:
            raise DriveAuthorizationError("No Google credentials found for the current user")

        credentials = self._build_credentials(token)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            refreshed = token.update_from_credentials(credentials)
            self._token_store.save(refreshed)

        service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        try:
            service.files().delete(fileId=drive_file_id).execute()
        except HttpError as exc:
            raise DriveExportError("Failed to delete document from Google Drive") from exc

    def _get_or_create_folder(self, service: Any, folder_name: str, parent_id: str | None = None) -> str:
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        try:
            results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
            files = results.get("files", [])

            if files:
                return files[0]["id"]

            # Create folder
            folder_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
            if parent_id:
                folder_metadata["parents"] = [parent_id]

            folder = service.files().create(body=folder_metadata, fields="id").execute()
            return folder["id"]
        except HttpError as exc:
            raise DriveExportError(f"Failed to find or create folder '{folder_name}'") from exc

    def _build_credentials(self, token: OAuthToken) -> Credentials:
        scopes = token.scope.split() if token.scope else DEFAULT_DRIVE_SCOPES
        return Credentials(
            token=token.access_token,
            refresh_token=token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.google_client_id,
            client_secret=self._settings.google_client_secret,
            scopes=scopes,
            id_token=token.id_token,
            expiry=token.token_expiry,
        )
