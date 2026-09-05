"""
SignalGraph — Chat Route
==========================
Endpoint:
  POST /api/chat — explain-only Q&A about SignalGraph's tracked
  companies and their detected signals. Never gives investment advice
  (enforced in the system prompt in app/chat/assistant.py).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user_id
from app.chat.assistant import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])

# anthropic is imported lazily inside the route handler so the server
# starts fine even if the package isn't installed — the rule-based
# (zero-cost) chat path never needs it.


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def post_chat(body: ChatRequest, user_id: str = Depends(get_current_user_id)):
    history = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        reply = answer_question(body.message, history)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
        )
    except Exception as exc:
        # Lazily check for anthropic-specific exceptions only when the
        # LLM path is active (ANTHROPIC_API_KEY configured). This avoids
        # a hard dependency on the anthropic package at import time.
        try:
            import anthropic
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
            )
        if isinstance(exc, anthropic.AuthenticationError):
            raise HTTPException(
                status_code=500,
                detail={"error": {"code": "INTERNAL_ERROR", "message": "Chat assistant is misconfigured (invalid API key)"}},
            )
        if isinstance(exc, anthropic.RateLimitError):
            raise HTTPException(
                status_code=503,
                detail={"error": {"code": "INTERNAL_ERROR", "message": "Chat assistant is rate-limited, try again shortly"}},
            )
        if isinstance(exc, anthropic.APIStatusError):
            raise HTTPException(
                status_code=502,
                detail={"error": {"code": "INTERNAL_ERROR", "message": f"Chat assistant error: {exc.message}"}},
            )
        if isinstance(exc, anthropic.APIConnectionError):
            raise HTTPException(
                status_code=502,
                detail={"error": {"code": "INTERNAL_ERROR", "message": "Could not reach the chat assistant"}},
            )
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
        )

    return ChatResponse(reply=reply)
