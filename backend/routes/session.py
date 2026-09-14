import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal
from models.chat_session import ChatSession
from services.auth_dependency import get_current_user_id
from datetime import datetime, timezone


router = APIRouter(prefix="/sessions", tags=["Sessions"],)

# Database Dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# Create session Endpoint
@router.post("")
async def create_session(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db),):
    thread_id = str(uuid.uuid4())

    session = ChatSession(thread_id=thread_id, user_id=user_id,)

    db.add(session)
    db.commit()
    db.refresh(session)

    return {"thread_id": session.thread_id, "message": "Chat session created successfully.",}


# Get sessions Endpoint
@router.get("")
async def get_sessions(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db),):
    
    sessions = (db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).all())

    return {
        "sessions": [
            {
                "thread_id": session.thread_id,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
            for session in sessions
        ]
    }


# Get single session Endpoint
@router.get("/{thread_id}")
async def get_session(thread_id: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db),):
    
    session = (db.query(ChatSession).filter(ChatSession.thread_id == thread_id, ChatSession.user_id == user_id,).first())

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.",)

    return {
        "thread_id": session.thread_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


# Continue session Endpoint
@router.post("/{thread_id}/continue")
def continue_session(thread_id: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db),):
    
    session = (db.query(ChatSession).filter(ChatSession.thread_id == thread_id, ChatSession.user_id == user_id,).first())

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.",)

    session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)

    return {
        "thread_id": session.thread_id,
        "message": "Chat session continued successfully.",
    }


# Delete session Endpoint
@router.delete("/{thread_id}")
def delete_session(thread_id: str, request: Request, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db),):
    
    session = (db.query(ChatSession).filter(ChatSession.thread_id == thread_id, ChatSession.user_id == user_id,).first())

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.",)

    checkpointer = request.app.state.checkpointer
    checkpointer.delete_thread(thread_id)

    db.delete(session)
    db.commit()

    return {
        "thread_id": thread_id,
        "message": "Chat session deleted successfully.",
    }


