export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Service unavailable" }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : error.result?.message || "Request rejected",
    );
  }
  return response.json() as Promise<T>;
}
export async function downloadReport(projectId: string) {
  const response = await fetch(
    `/api/v1/projects/${projectId}/executive-report`,
  );
  if (!response.ok)
    throw new Error("Run an assessment before exporting the report.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "northstar-executive-report.md";
  link.click();
  URL.revokeObjectURL(url);
}
