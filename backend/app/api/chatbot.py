from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.ai_models import ChatbotSession, ChatbotMessage
from app.api.deps import get_current_user
from app.services.chatbot_service import chatbot_service
from app.schemas.ai import ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/sessions")
def create_session(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = ChatbotSession(user_id=current_user.id, title="New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id}

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ChatbotSession).filter(ChatbotSession.user_id == current_user.id).order_by(ChatbotSession.created_at.desc()).all()

@router.get("/sessions/{id}/messages")
def list_messages(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.query(ChatbotSession).filter(
        ChatbotSession.id == id,
        ChatbotSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.query(ChatbotMessage).filter(
        ChatbotMessage.session_id == session.id,
    ).order_by(ChatbotMessage.created_at).all()
    return [{"id": message.id, "role": message.role, "content": message.content} for message in messages]

@router.post("/sessions/{id}/messages", response_model=ChatMessageResponse)
def send_message(id: str, request: ChatMessageRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.query(ChatbotSession).filter(ChatbotSession.id == id, ChatbotSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Save user message
    user_msg = ChatbotMessage(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)
    
    # Get history
    history_msgs = db.query(ChatbotMessage).filter(ChatbotMessage.session_id == session.id).order_by(ChatbotMessage.created_at).all()
    history = [{"role": msg.role, "content": msg.content} for msg in history_msgs]
    
    # Get response from RAG
    bot_response = chatbot_service.chat(request.message, history)
    
    # Save bot response
    bot_msg = ChatbotMessage(session_id=session.id, role="assistant", content=bot_response["response"], sources=bot_response["sources"])
    db.add(bot_msg)
    db.commit()
    
    return ChatMessageResponse(response=bot_response["response"], sources=[s["source"] for s in bot_response["sources"]])
