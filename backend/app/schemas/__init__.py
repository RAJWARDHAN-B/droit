"""API request and response schemas."""

from .document import (
    DocumentContent,
    DocumentSummary,
    DocumentSummaryRequest,
    DocumentSummaryText,
    PasteDocumentRequest,
    ProcessingJobResponse,
)
from .conversation import (
    ConversationDetail,
    ConversationMessageResponse,
    ConversationSummary,
    CreateConversationRequest,
    RenameConversationRequest,
    SendMessageRequest,
)
from .query import Citation, QueryRequest, QueryResponse
from .auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .settings import ConnectionTestResponse, LLMSettingsRequest, LLMSettingsResponse
from .drafting import (
    CreateDraftRequest,
    DraftClauseResponse,
    DraftDetail,
    DraftSummary,
    DraftTemplateRequest,
    DraftTemplateResponse,
    DraftVersionResponse,
    ExportDraftRequest,
    RegenerateClauseRequest,
    UpdateDraftClauseRequest,
)

__all__ = [
    "Citation",
    "ConversationDetail",
    "ConversationMessageResponse",
    "ConversationSummary",
    "CreateConversationRequest",
    "DocumentContent",
    "DocumentSummary",
    "DocumentSummaryRequest",
    "DocumentSummaryText",
    "PasteDocumentRequest",
    "ProcessingJobResponse",
    "QueryRequest",
    "QueryResponse",
    "RenameConversationRequest",
    "SendMessageRequest",
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "LLMSettingsRequest",
    "LLMSettingsResponse",
    "ConnectionTestResponse",
    "CreateDraftRequest",
    "DraftClauseResponse",
    "DraftDetail",
    "DraftSummary",
    "DraftTemplateRequest",
    "DraftTemplateResponse",
    "DraftVersionResponse",
    "ExportDraftRequest",
    "RegenerateClauseRequest",
    "UpdateDraftClauseRequest",
]