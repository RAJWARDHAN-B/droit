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

export type CurrentUser = {
  id: string;
  email: string;
  role: string;
};

export type SummaryStyle = "legal" | "layman";

export type DocumentSummaryText = {
  document_id: string;
  style: SummaryStyle;
  summary: string;
  provider: string;
  model: string;
  generated_at: string;
  cached: boolean;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  provider: string | null;
  model: string | null;
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  document_id: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
};

export type DraftTemplate = {
  id: string;
  slug: string;
  name: string;
  document_type: string;
  input_schema: Record<string, { label: string; required?: boolean }>;
  clause_outline: Array<{ heading: string; purpose?: string }>;
  is_builtin: boolean;
};

export type DraftClause = {
  id: string;
  ordinal: number;
  heading: string;
  body: string;
  rationale: string;
  risk_notes: string[];
  source: "generated" | "edited" | "template";
  version: number;
};

export type DraftRiskBreakdown = {
  score?: number;
  missing_clauses?: string[];
  asymmetric_terms?: string[];
  auto_renewal_terms?: string[];
  category_scores?: Record<string, number>;
};

export type Draft = {
  id: string;
  title: string;
  template_id: string;
  status: "draft" | "final";
  updated_at: string;
  inputs: Record<string, string>;
  risk_breakdown: DraftRiskBreakdown;
  clauses: DraftClause[];
  version: number;
};

export type DraftSummary = Pick<Draft, "id" | "title" | "template_id" | "status" | "updated_at">;

export type DraftVersion = {
  version: number;
  title: string;
  clause_count: number;
  created_by: string;
  created_at: string;
};

export type DraftTemplateInput = {
  name: string;
  document_type: string;
  input_schema: Record<string, { label: string; required?: boolean }>;
  clause_outline: Array<{ heading: string; purpose?: string }>;
};

export type DraftExportFormat = "docx" | "pdf";

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
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event("droit:auth-expired"));
    }
    throw new Error(await readError(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<CurrentUser> {
  const result = await request<{ user: CurrentUser }>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return result.user;
}

export function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me");
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
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

export function getDocumentSummary(
  documentId: string,
  style: SummaryStyle,
  refresh = false,
): Promise<DocumentSummaryText> {
  return request<DocumentSummaryText>(`/documents/${documentId}/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ style, refresh }),
  });
}

export function createConversation(documentId: string | null): Promise<Conversation> {
  return request<Conversation>("/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId }),
  });
}

export function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/conversations");
}

export function getConversation(conversationId: string): Promise<Conversation> {
  return request<Conversation>(`/conversations/${conversationId}`);
}

export function sendConversationMessage(
  conversationId: string,
  question: string,
): Promise<Conversation> {
  return request<Conversation>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
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

export function listDraftTemplates(): Promise<DraftTemplate[]> {
  return request<DraftTemplate[]>("/drafting/templates");
}

export function listDrafts(): Promise<DraftSummary[]> {
  return request<DraftSummary[]>("/drafting/drafts");
}

export function getDraft(draftId: string): Promise<Draft> {
  return request<Draft>(`/drafting/drafts/${draftId}`);
}

export function deleteDraft(draftId: string): Promise<void> {
  return request<void>(`/drafting/drafts/${draftId}`, { method: "DELETE" });
}

export function listDraftVersions(draftId: string): Promise<DraftVersion[]> {
  return request<DraftVersion[]>(`/drafting/drafts/${draftId}/versions`);
}

export function restoreDraftVersion(draftId: string, version: number): Promise<Draft> {
  return request<Draft>(`/drafting/drafts/${draftId}/versions/${version}/restore`, {
    method: "POST",
  });
}

export function createDraftTemplate(payload: DraftTemplateInput): Promise<DraftTemplate> {
  return request<DraftTemplate>("/drafting/templates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateDraftTemplate(
  templateId: string,
  payload: DraftTemplateInput,
): Promise<DraftTemplate> {
  return request<DraftTemplate>(`/drafting/templates/${templateId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteDraftTemplate(templateId: string): Promise<void> {
  return request<void>(`/drafting/templates/${templateId}`, { method: "DELETE" });
}

export function createDraft(
  templateId: string,
  title: string,
  inputs: Record<string, string>,
): Promise<Draft> {
  return request<Draft>("/drafting/drafts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template_id: templateId, title, inputs }),
  });
}

export function updateDraftClause(
  draftId: string,
  clauseId: string,
  heading: string,
  body: string,
): Promise<Draft> {
  return request<Draft>(`/drafting/drafts/${draftId}/clauses/${clauseId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ heading, body }),
  });
}

export function regenerateDraftClause(
  draftId: string,
  clauseId: string,
  instruction?: string,
): Promise<Draft> {
  return request<Draft>(`/drafting/drafts/${draftId}/clauses/${clauseId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction: instruction || null }),
  });
}

export async function exportDraft(
  draftId: string,
  format: DraftExportFormat,
  filename: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/drafting/drafts/${draftId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format }),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await readError(response));
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${filename || "droit-draft"}.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}
