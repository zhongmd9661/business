"""Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Auth ---

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Tasks ---

class TaskCreateResponse(BaseModel):
    task_id: int
    status: str


class TaskResponse(BaseModel):
    id: int
    user_id: int
    batch_name: str
    status: str
    file_count: int
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class TaskFileResponse(BaseModel):
    id: int
    task_id: int
    filename: str
    file_type: str
    parsed: bool

    model_config = {"from_attributes": True}


# --- Rules ---

class AuditRuleCreate(BaseModel):
    category: str
    rule_name: str
    clause: str
    level: str = "中"
    description: Optional[str] = None
    check_expression: Optional[str] = None
    source_document: Optional[str] = None
    enabled: bool = True


class AuditRuleUpdate(BaseModel):
    category: Optional[str] = None
    rule_name: Optional[str] = None
    clause: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    check_expression: Optional[str] = None
    source_document: Optional[str] = None
    enabled: Optional[bool] = None


class AuditRuleResponse(BaseModel):
    id: int
    category: str
    rule_name: str
    clause: str
    level: str
    description: Optional[str] = None
    check_expression: Optional[str] = None
    source_document: Optional[str] = None
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Sync ---

class SyncStatusResponse(BaseModel):
    pending_changes: int
    documents: list[dict]


class SyncApplyRequest(BaseModel):
    apply: bool = True


class SyncHistoryResponse(BaseModel):
    id: int
    trigger_type: str
    document_name: str
    rules_added: int
    rules_modified: int
    rules_deleted: int
    status: str
    operated_at: Optional[str] = None

    model_config = {"from_attributes": True}
