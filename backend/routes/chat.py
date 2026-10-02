from fastapi import Depends, HTTPException, APIRouter, Request
from sqlalchemy.orm import Session
from services.auth_dependency import get_current_user_id
from models.chat_session import ChatSession
from schemas.auth import ChatRequest
from database import SessionLocal
from datetime import datetime, timezone
from langchain.messages import HumanMessage

from services.session_title_service import generate_session_title


router = APIRouter(prefix="/chat", tags=["Chat"],)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Chat Endpoint
@router.post('')
async def chat(data: ChatRequest, request: Request, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    session =  db.query(ChatSession).filter(ChatSession.thread_id == data.thread_id, ChatSession.user_id == user_id,).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.",)
    
    agent = request.app.state.agent

    config = {
        "configurable": {
            "thread_id": data.thread_id
        }
    }

    state_before = agent.get_state(config)
    existing_messages = state_before.values.get("messages", [])
    messages_before = len(existing_messages)

    # Use the current input for a completely new session.
    # If this is an older untitled session, recover its actual first message.
    title_source_message = data.user_input

    if not session.title:
        first_human_message = next(
        (
            message
            for message in existing_messages
            if getattr(message, "type", None) == "human"
        ),
        None,
    )

        if first_human_message is not None:
            first_content = first_human_message.content

            if isinstance(first_content, str) and first_content.strip():
                title_source_message = first_content

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content=data.user_input)
            ]
        },
        config=config,
    )

    all_messages = result["messages"]

    # Only look at messages added in THIS turn (not the full history)
    new_messages = all_messages[messages_before:]

    tool_calls_made = []
    for msg in new_messages:
        for tc in getattr(msg, "tool_calls", []):
            tool_calls_made.append({
                "name": tc["name"],
                "args": tc["args"],
            })

    final_content = all_messages[-1].content
    final_text = final_content[0]["text"] if isinstance(final_content, list) else final_content

    if not session.title:
        session.title = generate_session_title(title_source_message)

    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return {
        "thread_id": data.thread_id,
        "title": session.title,
        "message": final_text,
        "tool_calls": tool_calls_made,
    }


# Get Chat History
@router.get("/{thread_id}")
async def get_chat_history(thread_id: str, request: Request, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db),):

    session = (db.query(ChatSession).filter(ChatSession.thread_id == thread_id, ChatSession.user_id == user_id,).first())

    if not session:
        raise HTTPException(status_code=404,detail="Chat session not found.",)

    agent = request.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    state = agent.get_state(config)
    messages = state.values.get("messages", [])

    return {
        "thread_id": thread_id,
        "messages": [
            {
                "role": message.type,
                "content": message.content,
                # Include tool_calls for AI messages so the frontend
                # can display which tool was invoked and with what args
                "tool_calls": [
                    {"name": tc["name"], "args": tc["args"]}
                    for tc in getattr(message, "tool_calls", [])
                ],
            }
            for message in messages
        ],
    }