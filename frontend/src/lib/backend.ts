const configuredBackendUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
    (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

export function backendUrl(path: string): string {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return configuredBackendUrl ? `${configuredBackendUrl}${normalizedPath}` : normalizedPath;
}
