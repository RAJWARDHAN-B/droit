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
  risk_breakdown: Record<string, unknown> | null;
};

export type DocumentContent = {
  id: string;
  filename: string;
  text: string;
  anonymized: boolean;
};

export type ProcessingJob = {
  job_id: string;
  document_id: string;
  filename: string;
  document_status: DocumentStatus;
  stage: string;
  error_message: string | null;
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

export type LLMSettings = {
  provider: string;
  model: string;
  base_url: string | null;
  api_key_configured: boolean;
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
  const headers = new Headers(init?.headers);
  const token = typeof window !== "undefined" ? window.localStorage.getItem("droit_access_token") : null;
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<void> {
  const result = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  window.localStorage.setItem("droit_access_token", result.access_token);
}

export function getLLMSettings(): Promise<LLMSettings> {
  return request<LLMSettings>("/settings/llm");
}

export function updateLLMSettings(payload: {
  provider: string;
  model: string;
  base_url: string | null;
  api_key: string | null;
}): Promise<LLMSettings> {
  return request<LLMSettings>("/settings/llm", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function testLLMSettings(payload: {
  provider: string;
  model: string;
  base_url: string | null;
  api_key: string | null;
}): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>("/settings/llm/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>("/documents");
}

export function uploadDocument(file: File): Promise<ProcessingJob> {
  const body = new FormData();
  body.append("file", file);
  return request<ProcessingJob>("/documents/upload", { method: "POST", body });
}

export function getProcessingJob(jobId: string): Promise<ProcessingJob> {
  return request<ProcessingJob>(`/jobs/${jobId}`);
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

export function getDocumentContent(documentId: string): Promise<DocumentContent> {
  return request<DocumentContent>(`/documents/${documentId}/content`);
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
