const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export type DocumentSummary = {
  id: string;
  filename: string;
  media_type: string | null;
  status: DocumentStatus;
  created_at: string;
  chunk_count: number;
  character_count: number | null;
  pii_count: number | null;
  risk_score: number | null;
};

export type ProcessingJob = {
  job_id: string;
  document_id: string;
  filename: string;
  document_status: DocumentStatus;
  stage: string;
};

export type Citation = {
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  score: number;
  excerpt: string;
};

export type QueryAnswer = {
  answer: string;
  provider: string;
  model: string;
  citations: Citation[];
};

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail[0].msg ?? "Request failed";
    }
  } catch {
    // Fall through to the status-based message below.
  }
  return `Request failed with status ${response.status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, init);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>("/documents");
}

export function uploadDocument(file: File): Promise<ProcessingJob> {
  const body = new FormData();
  body.append("file", file);
  return request<ProcessingJob>("/documents/upload", { method: "POST", body });
}

export function pasteDocument(
  title: string,
  text: string,
): Promise<ProcessingJob> {
  return request<ProcessingJob>("/documents/paste", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, text }),
  });
}

export function deleteDocument(documentId: string): Promise<void> {
  return request<void>(`/documents/${documentId}`, { method: "DELETE" });
}

export function askQuestion(
  question: string,
  documentId: string | null,
): Promise<QueryAnswer> {
  return request<QueryAnswer>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      document_id: documentId,
    }),
  });
}
