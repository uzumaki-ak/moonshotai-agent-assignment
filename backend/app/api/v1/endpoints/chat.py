# this file exposes grounded dataset chat endpoints
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.chat.assistant import answer_data_question

router = APIRouter()


@router.post("/ask", response_model=ChatAskResponse)
async def ask_chat(payload: ChatAskRequest, db: Session = Depends(get_db)) -> dict:
    # this endpoint answers one grounded dataset question
    return await answer_data_question(db, payload.question, payload.brand_ids)
