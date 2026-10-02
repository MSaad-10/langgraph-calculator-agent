import os
from typing import Any, cast

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from sqlalchemy import update

from agent.agent import agent_builder
from database import SessionLocal
from models.chat_session import ChatSession
from services.session_title_service import generate_session_title


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")


connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
    "row_factory": dict_row,
}


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []

        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    text_parts.append(text)

        return " ".join(text_parts)

    return str(content or "")


def backfill_session_titles() -> None:
    with ConnectionPool(
        conninfo=DATABASE_URL,
        max_size=5,
        kwargs=connection_kwargs,
    ) as pool:
        checkpointer = PostgresSaver(
            cast(ConnectionPool[Connection[dict[str, Any]]], pool)
        )
        checkpointer.setup()

        agent = agent_builder.compile(checkpointer=checkpointer)
        db = SessionLocal()

        try:
            sessions = (
                db.query(ChatSession)
                .filter(ChatSession.title.is_(None))
                .all()
            )

            updated_count = 0

            for session in sessions:
                config = {
                    "configurable": {
                        "thread_id": session.thread_id,
                    }
                }

                state = agent.get_state(config)
                messages = state.values.get("messages", [])

                first_human_message = next(
                    (
                        message
                        for message in messages
                        if getattr(message, "type", None) == "human"
                    ),
                    None,
                )

                if first_human_message is None:
                    print(f"Skipped empty session {session.thread_id}")
                    continue

                first_message_text = content_to_text(
                    first_human_message.content
                )

                if not first_message_text.strip():
                    print(f"Skipped session {session.thread_id}: empty message")
                    continue

                title = generate_session_title(first_message_text)

                db.execute(
                    update(ChatSession)
                    .where(
                        ChatSession.id == session.id,
                        ChatSession.title.is_(None),
                    )
                    .values(
                        title=title,
                        updated_at=session.updated_at,
                    )
                )
                db.commit()

                updated_count += 1
                print(f"{session.thread_id} -> {title}")

            print(f"Updated {updated_count} session titles.")

        finally:
            db.close()


if __name__ == "__main__":
    backfill_session_titles()