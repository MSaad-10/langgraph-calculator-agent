import os
from contextlib import asynccontextmanager
from typing import Any, cast
from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agent.agent import agent_builder
from routes.auth import router as auth_router
from routes.session import router as session_router
from routes.chat import router as chat_router

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
    "row_factory": dict_row,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    with ConnectionPool(conninfo=DATABASE_URL, max_size=10, kwargs=connection_kwargs,) as pool:
        checkpointer = PostgresSaver(cast(ConnectionPool[Connection[dict[str, Any]]], pool))
        checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.agent = agent_builder.compile(checkpointer=checkpointer)
        yield

app = FastAPI(title="Calculator Agent API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(session_router)
app.include_router(chat_router)