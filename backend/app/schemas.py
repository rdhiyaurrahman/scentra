from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .models import INTENTS, PRIORITIES, STATUSES

MarketplaceCode = Literal["shopee", "tiktok", "lazada"]


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageIn(BaseModel):
    message_text: str = Field(min_length=1, max_length=4000)
    marketplace_message_time: Optional[datetime] = None


class ConversationIn(MessageIn):
    marketplace_code: MarketplaceCode
    customer_name: str = Field(min_length=1, max_length=120)
    external_reference: Optional[str] = Field(default=None, max_length=64)
    product_hint: Optional[str] = Field(default=None, max_length=160)
    # Kalau True dan referensi sudah dipakai, pesan ditambahkan ke percakapan itu
    # alih-alih membuat percakapan baru (AC-02).
    merge_into_existing: bool = True


class ConversationPatch(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_user_id: Optional[int] = None

    def validated(self) -> "ConversationPatch":
        if self.status is not None and self.status not in STATUSES:
            raise ValueError(f"Status tidak dikenal: {self.status}")
        if self.priority is not None and self.priority not in PRIORITIES:
            raise ValueError(f"Prioritas tidak dikenal: {self.priority}")
        return self


class ClassificationPatch(BaseModel):
    intent: str

    def validated(self) -> "ClassificationPatch":
        if self.intent not in INTENTS:
            raise ValueError(f"Intent tidak dikenal: {self.intent}")
        return self


class NoteIn(BaseModel):
    note_text: str = Field(min_length=1, max_length=2000)


class ActionIn(BaseModel):
    action_text: str = Field(min_length=1, max_length=500)


class ReplyEditIn(BaseModel):
    reply_text: str = Field(min_length=1, max_length=4000)
