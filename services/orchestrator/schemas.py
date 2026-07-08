from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: Any
    name: str | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "auto"
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None


class OrchestrateRequest(ChatRequest):
    improve_prompt: bool | Literal["auto"] | None = None
    use_tools: bool | Literal["auto"] | None = None
    prompt_model: str | None = None


class ImprovePromptRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str = "prompt"
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, gt=0)


class ConsultPromptRequest(BaseModel):
    prompt: str = Field(min_length=1)
    preferred_language: str | None = None


class ToolCallRequest(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class UpdateVirtualModelRequest(BaseModel):
    virtual_model: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    improve_prompt: bool | Literal["auto"] = False
    tools: bool | Literal["auto"] = False


class UpdatePromptImproverRequest(BaseModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, gt=0)


class PatchMcpToolsRequest(BaseModel):
    enabled: bool | None = None
    set_tools: list[str] | None = None
    allow_tools: list[str] | None = None
    deny_tools: list[str] | None = None
