import uuid
from datetime import datetime
from typing import Any, List, Optional

from loguru import logger
from pydantic import BaseModel, Field, validator
from beanie import Document, Link

# ==========================
# Beanie Document Models
# ==========================

class Conversation(Document):
    title: Optional[str] = None
    archived: bool = False
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    messageCount: int = 0
    # _participants: List[str] = Field(default_factory=list)
    createdBy: Optional[str] = None
    isRemove: bool = False

    @validator("createdBy", pre=True)
    def str_created_by(cls, v):
        return str(v) if v is not None else v

    class Settings:
        name = "socialize:conversations"

class Message(Document):
    id: Optional[str] = Field(default=None, alias="_id") 
    conversation_id: str = Field(alias="conversationId")
    body: Optional[str] = None
    role: Optional[str] = None
    contentType: Optional[str] = None
    userId: Optional[str] = None
    language_code: str = "english"
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    extra_metadata: Optional[dict] = None

    @validator("id", pre=True)
    def str_id(cls, v):
        return str(v) if v is not None else v

    @validator("conversation_id", pre=True)
    def str_conversation_id(cls, v):
        return str(v) if v is not None else v

    @validator("userId", pre=True)
    def str_user_id(cls, v):
        return str(v) if v is not None else v

    class Settings:
        name = "socialize:messages"
        use_state_management = True

class Attachment(Document):
    attachment_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    message_id: Optional[str] = None
    file_data: str
    file_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("attachment_id", pre=True)
    def str_attachment_id(cls, v):
        return str(v) if v is not None else v

    @validator("message_id", pre=True)
    def str_message_id(cls, v):
        return str(v) if v is not None else v

    class Settings:
        name = "attachments"

# ==========================
# Pydantic Models (保留)
# ==========================

class ConversationModel(BaseModel):
    id: str = Field(alias="_id")
    title: Optional[str] = None
    archived: Optional[bool] = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}

    @validator("id", pre=True)
    def str_id(cls, v):
        return str(v)

class ConversationCreateModel(BaseModel):
    title: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }

class ConversationUpdateModel(BaseModel):
    title: Optional[str]

    model_config = {
        "from_attributes": True,
    }

class AttachmentModel(BaseModel):
    attachment_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    file_data: str
    file_type: str
    created_at: datetime

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}

class AttachmentUploadResponse(BaseModel):
    attachment_id: uuid.UUID
    file_type: str

    model_config = {"from_attributes": True}

class MessageCreateModel(BaseModel):
    content: dict
    extra_metadata: Optional[dict] = None

    model_config = {
        "from_attributes": True,
        "extra": "allow",
    }

class MessageModel(BaseModel):
    message_id: str = Field(alias="_id")
    conversation_id: str
    message_number: int
    content: dict
    language_code: Optional[str] = "english"
    created_at: datetime
    updated_at: datetime
    extra_metadata: Optional[dict] = None

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}

    @validator("message_id", pre=True)
    def str_message_id(cls, v):
        return str(v)

class MessageWithConversationModel(BaseModel):
    message: MessageModel
    conversation: ConversationModel

    model_config = {
        "from_attributes": True,
    }
