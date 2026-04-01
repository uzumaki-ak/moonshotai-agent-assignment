# this file defines grounded chat request and response schemas
from typing import Optional

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    # this schema submits one grounded data question
    question: str = Field(min_length=3, max_length=1200)
    brand_ids: list[int] = Field(default_factory=list)


class ChatCitation(BaseModel):
    # this schema returns one source pointer used for the answer
    type: str
    label: str
    url: Optional[str] = None


class ChatAskResponse(BaseModel):
    # this schema returns one grounded answer with provenance
    answer: str
    provider: Optional[str] = None
    model: Optional[str] = None
    brands: list[str] = Field(default_factory=list)
    citations: list[ChatCitation] = Field(default_factory=list)
