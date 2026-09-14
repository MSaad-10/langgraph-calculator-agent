from fastapi import Depends, HTTPException, APIRouter, Request
from sqlalchemy.orm import Session
from services.auth_dependency import get_current_user_id
from models.chat_session import ChatSession
from schemas.auth import ChatRequest
from database import SessionLocal
from datetime import datetime, timezone
from langchain.messages import HumanMessage


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

    # Snapshot existing message count BEFORE this turn so we only
    # collect tool calls that belong to the current invocation.
    state_before = agent.get_state(config)
    messages_before = len(state_before.values.get("messages", []))

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

    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "thread_id": data.thread_id,
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