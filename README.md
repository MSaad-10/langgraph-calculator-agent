# Arithma — Calculator Agent

A full-stack AI-powered calculator application built with **LangGraph**, **FastAPI**, and **Vanilla JS**. Arithma is a focused arithmetic assistant that uses a language model to understand natural-language math queries and executes calculations through reliable, deterministic tool calls — never performing arithmetic itself. The application features automated AI session title generation, a complete authentication system with email verification, JWT-based sessions, and multi-turn persistent chat history checkpointed to PostgreSQL.

---

## ✨ Features

- 🤖 **LangGraph ReAct Agent** — LLM decides which calculator tool to invoke; arithmetic results are deterministic and accurate.
- 🏷️ **AI-Generated Session Titles** — Sessions are automatically titled (3–6 words) based on mathematical intent using Gemini (`gemini-3.5-flash`), with fallback heuristics.
- 🛡️ **Robust Tool Error Handling** — Math domain errors (division by zero, negative square roots, negative power of zero, modulus by zero) return descriptive diagnostic messages to the agent rather than crashing.
- 🔐 **Full Auth System** — Signup → OTP email verification → Login → JWT access tokens.
- 🔑 **Password Reset** — Secure token-based email reset flow.
- 💬 **Persistent Chat Sessions** — Every conversation is checkpointed to PostgreSQL via LangGraph (`langgraph-checkpoint-postgres`).
- 📜 **Chat History & Tool Insights** — Full message history (human, AI, tool calls) per session with insight into tools called and arguments passed.
- 🖥️ **Single-Page Frontend** — Vanilla JS SPA with Markdown (`marked`), LaTeX math rendering (`KaTeX`), and XSS sanitization (`DOMPurify`), featuring an active session list with live title updates.

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Web Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| AI / Agent Framework | [LangGraph](https://langchain-ai.github.io/langgraph/) + [LangChain](https://python.langchain.com/) |
| LLM & Title Model | Google Gemini (`gemini-3.5-flash`) via `langchain-google-genai` / `google-genai` |
| Agent Checkpointing | `langgraph-checkpoint-postgres` (PostgreSQL) |
| ORM | [SQLAlchemy](https://www.sqlalchemy.org/) (v2, mapped columns) |
| Database Driver | `psycopg` / `psycopg-pool` |
| Auth & Passwords | JWT (`PyJWT`), `pwdlib` (Argon2 password hashing) |
| Email Service | Python standard `smtplib` over STARTTLS |
| Validation | [Pydantic](https://docs.pydantic.dev/) v2 |
| Config | `python-dotenv` |

### Frontend
| Layer | Technology |
|---|---|
| Build Tool / Dev Server | [Vite](https://vitejs.dev/) v8 |
| Language | Vanilla JavaScript (ES Modules) |
| Styling | Vanilla CSS |
| Markdown Rendering | [`marked`](https://marked.js.org/) |
| Math Rendering | [`KaTeX`](https://katex.org/) |
| Sanitization | [`DOMPurify`](https://github.com/cure53/DOMPurify) |

### Infrastructure
| Component | Technology |
|---|---|
| Database | PostgreSQL |
| SMTP Server | Gmail (or any STARTTLS-compatible SMTP server) |

---

## 🗂️ Project Architecture

```
calculator_agent/
├── .env.example                       # Template for environment variables
├── .gitignore
├── requirements.txt                   # Python dependencies
│
├── backend/
│   ├── main.py                        # FastAPI app entry point, lifespan, checkpointer & router registration
│   ├── database.py                    # SQLAlchemy engine + SessionLocal factory
│   │
│   ├── agent/
│   │   ├── agent.py                   # LangGraph StateGraph definition (nodes, edges, router)
│   │   └── tools.py                   # Calculator tools: add, subtract, multiply, divide, power, modulus, square_root
│   │
│   ├── models/                        # SQLAlchemy ORM table definitions
│   │   ├── user.py                    # users table + Base declarative class
│   │   ├── email_verification.py      # email_verifications table (pre-signup OTP staging)
│   │   ├── chat_session.py            # chat_sessions table (thread_id registry + dynamic titles)
│   │   └── password_reset.py          # password_reset_tokens table
│   │
│   ├── routes/                        # FastAPI routers
│   │   ├── auth.py                    # /auth — signup, verify-otp, login, forgot/reset password, resend-otp
│   │   ├── session.py                 # /sessions — CRUD for chat sessions
│   │   └── chat.py                    # /chat — send message, get history
│   │
│   ├── schemas/
│   │   └── auth.py                    # Pydantic request/response models
│   │
│   └── services/
│       ├── auth_service.py            # Password hashing / verification (pwdlib)
│       ├── auth_dependency.py         # FastAPI dependency: Bearer token → user_id
│       ├── jwt_services.py            # JWT creation and decoding
│       ├── email_service.py           # SMTP: OTP email + password reset email
│       ├── otp_service.py             # OTP generation, hashing, expiry
│       ├── password_reset_service.py  # Reset token generation, hashing, expiry
│       └── session_title_service.py   # AI session title generation & fallback logic (Gemini)
│
└── frontend/
    ├── index.html                     # SPA shell
    ├── package.json                   # Frontend dependencies and Vite scripts
    ├── vite.config.js                 # Vite dev server with reverse proxy for /auth, /sessions, /chat
    └── src/
        ├── main.js                    # All frontend logic (routing, auth, sessions, chat UI, KaTeX/marked)
        └── style.css                  # Modern UI styles, animations, responsive layout
```

---

## 🗄️ Database Schema

### `users`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, auto-increment |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `password_hash` | VARCHAR(255) | NOT NULL |
| `is_verified` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now(), auto-updated |

---

### `email_verifications`
Temporary staging table for users who have signed up but not yet confirmed their OTP.

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, auto-increment |
| `username` | VARCHAR(50) | NOT NULL |
| `email` | VARCHAR(255) | NOT NULL |
| `password_hash` | VARCHAR(255) | NOT NULL |
| `otp_hash` | VARCHAR(255) | NOT NULL |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `attempts` | INTEGER | NOT NULL, default `0` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |

> Row is **deleted** and a `users` row is **created** upon successful OTP verification.

---

### `chat_sessions`
Tracks session metadata for each conversation thread.

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, auto-increment |
| `thread_id` | VARCHAR(100) | UNIQUE, NOT NULL, indexed |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, indexed |
| `title` | VARCHAR(80) | NULLABLE |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now(), auto-updated |

> - `thread_id` is a UUID-v4 string that acts as the key for LangGraph's PostgreSQL checkpointer.
> - `title` is generated dynamically using Gemini (`session_title_service`) on the initial message turn.

---

### `password_reset_tokens`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, auto-increment |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL |
| `token_hash` | VARCHAR(255) | UNIQUE, NOT NULL |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `used` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |

> Tokens are single-use. All previous unused tokens for a user are invalidated on each new reset request.

---

### LangGraph Checkpointer Tables (auto-created by LangGraph)
LangGraph automatically creates its own PostgreSQL tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) during application startup via `checkpointer.setup()` in [backend/main.py](file:///d:/Office/LangGraph/calculator_agent/backend/main.py). These tables store message states, graph checkpoints, and execution history indexed by `thread_id`.

---

## 🔄 Data Flow

### 1. Signup Flow
```
User fills signup form
  → POST /auth/signup
    → Check username/email uniqueness in `users`
    → Hash password (Argon2)
    → Generate 6-digit OTP → hash it
    → Insert row into `email_verifications`
    → Send OTP email via SMTP
  ← 200: "OTP sent to your email."

User enters OTP
  → POST /auth/verify-otp
    → Look up `email_verifications` by email (latest row)
    → Check expiry (5 min) and attempt count (max 5)
    → Verify OTP hash
    → On success: INSERT into `users` (is_verified=True)
               + DELETE from `email_verifications`
  ← 200: "Account created successfully."
```

### 2. Login Flow
```
User submits credentials
  → POST /auth/login
    → Query `users` by username
    → Check is_verified == True
    → Verify password hash (Argon2)
    → Create JWT (payload: {sub: user_id, exp: now + 60min})
  ← 200: { access_token, token_type: "bearer" }

JWT stored in frontend (localStorage / memory)
  → Attached as: Authorization: Bearer <token>
  → All protected routes use get_current_user_id() dependency
     which decodes JWT → extracts user_id
```

### 3. Chat & Title Generation Flow
```
User creates a session
  → POST /sessions  [JWT required]
    → Generate UUID → thread_id
    → INSERT into `chat_sessions` (title=None)
  ← 200: { thread_id, title: null, message: "Chat session created successfully." }

User sends a message
  → POST /chat  [JWT required]
    Body: { thread_id, user_input }
    → Validate thread_id belongs to current user in `chat_sessions`
    → Snapshot agent state BEFORE invoke (count existing messages)
    → agent.invoke({ messages: [HumanMessage(user_input)] }, config={thread_id})

        LangGraph Agent Loop:
        ┌─────────────────────────────────────────────────────────┐
        │ START → llm_call                                        │
        │   LLM receives [SystemMessage + all history + new msg]  │
        │   LLM returns: either tool_calls or final response      │
        │                                                         │
        │ if tool_calls → tool_node                               │
        │   Execute each tool (add/subtract/multiply/etc.)        │
        │   Catch math errors & return safe diagnostic message    │
        │   Return ToolMessage(content) for each                  │
        │   → loop back to llm_call                               │
        │                                                         │
        │ if no tool_calls → END                                  │
        └─────────────────────────────────────────────────────────┘

    → All messages checkpointed to PostgreSQL automatically
    → Extract only NEW messages from this turn
    → Collect tool_calls made this turn
    → If session has no title yet:
        Generate 3-6 word title via Gemini (session_title_service)
        Save to session.title
    → Update chat_sessions.updated_at
  ← 200: { thread_id, title, message: <final AI text>, tool_calls: [...] }

User loads history
  → GET /chat/{thread_id}  [JWT required]
    → Validate session ownership
    → agent.get_state(config={thread_id})
    → Return all messages with role + content + tool_calls
  ← 200: { thread_id, messages: [...] }
```

### 4. Password Reset Flow
```
User requests reset
  → POST /auth/forgot-password  { email }
    → Look up user by email (silent if not found)
    → Invalidate all existing unused tokens
    → Generate secure random token → hash it
    → INSERT into `password_reset_tokens`
    → Send email with reset link: FRONTEND_URL/?page=reset-password&token=<raw_token>
  ← 200: (always same message, prevents email enumeration)

User clicks reset link → frontend parses token from URL
  → POST /auth/reset-password  { token, password }
    → Hash the received token
    → Look up `password_reset_tokens` by token_hash
    → Validate: not used, not expired
    → Update user.password_hash with new hashed password
    → Mark token as used
  ← 200: "Password reset successfully"
```

---

## ⚙️ LangGraph Agent & Tool Architecture

The agent is a **ReAct-style** graph built with LangGraph's `StateGraph`:

```
           START
             │
             ▼
        ┌──────────┐
        │ llm_call │  ← Gemini LLM + bound tools
        └──────────┘
             │
     should_continue()
      ┌──────┴──────┐
      │             │
 tool_calls?       END
      │
      ▼
 ┌───────────┐
 │ tool_node │  ← Executes arithmetic tools
 └───────────┘
      │
      └──────────► llm_call  (loop back)
```

**State** (`AgentState`):
- `messages` — Full conversation history (inherited from `MessagesState`).
- `llm_calls` — Counter tracking LLM invocations in the current turn.

### Available Tools

All calculation operations are performed deterministically via tools defined in [backend/agent/tools.py](file:///d:/Office/LangGraph/calculator_agent/backend/agent/tools.py). Rather than throwing unhandled exceptions on invalid arithmetic, each tool returns a safe, explanatory string so the agent can inform the user gracefully:

| Tool | Operation | Behavior & Error Handling |
|---|---|---|
| `add(a, b)` | `a + b` | Adds two integers |
| `subtract(a, b)` | `a - b` | Subtracts `b` from `a` (supports `int` or `float`) |
| `multiply(a, b)` | `a * b` | Multiplies two integers |
| `divide(a, b)` | `a / b` | Divides `a` by `b`. Returns `"Divisor cannot be zero."` on `b == 0` |
| `power(a, b)` | `a ** b` | Exponentiation. Returns `"Cannot raise 0 to a negative power."` on `a == 0 and b < 0` |
| `modulus(a, b)` | `a % b` | Modulo operation. Returns `"Divisor cannot be zero."` on `b == 0` |
| `square_root(number)` | `number ** 0.5` | Square root. Returns `"Number cannot be negative."` on `number < 0` |

### Dynamic Session Title Generation

The session title service in [backend/services/session_title_service.py](file:///d:/Office/LangGraph/calculator_agent/backend/services/session_title_service.py) automatically generates titles for chat threads:
- **LLM Prompting**: Prompts Gemini (`gemini-3.5-flash`) with strict system rules to produce a 3–6 word title describing the calculation intent without revealing the result.
- **Security & Untrusted Input**: Treats user messages strictly as untrusted content; does not execute commands embedded within prompts.
- **Sanitization**: Cleans quotation marks, formatting artifacts, markdown headers, and punctuation, enforcing a maximum length of 80 characters.
- **Resilient Fallback**: If the model is unreachable, an intelligent regex fallback extracts the initial calculation terms from the user's message.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (running locally or remote)
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) enabled (or any SMTP provider)
- A [Google AI Studio API Key](https://aistudio.google.com/app/apikey)

---

### 1. Clone the Repository

```bash
git clone https://github.com/MSaad-10/langgraph-calculator-agent.git
cd calculator_agent
```

---

### 2. Configure Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=your_google_api_key_here

DATABASE_URL="postgresql://postgres:password@localhost:5432/calculator_db"

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_app_password

FRONTEND_URL=http://localhost:5173

JWT_SECRET_KEY=your_generated_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

> **Generate a secure JWT secret key:**
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

### 3. Set Up the Backend

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Create the PostgreSQL database first (if not already created):
# CREATE DATABASE calculator_db;

# Create application tables in PostgreSQL:
cd backend
python -c "from database import engine; from models.user import Base; import models.email_verification, models.chat_session, models.password_reset; Base.metadata.create_all(bind=engine)"
```

> [!NOTE]
> The LangGraph checkpointing tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) are created automatically when the FastAPI application starts up.

---

### 4. Run the Backend

```bash
# From the backend/ directory
uvicorn main:app --reload
```

The API will be running at `http://localhost:8000`.
- Interactive Swagger docs: `http://localhost:8000/docs`
- ReDoc docs: `http://localhost:8000/redoc`

---

### 5. Set Up and Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.
Vite is preconfigured to proxy `/auth`, `/sessions`, and `/chat` directly to the FastAPI server at `http://127.0.0.1:8000`.

---

## 📡 API Reference

### Authentication — `/auth`

| Method | Endpoint                | Description                       | Auth Required |
|--------|-------------------------|-----------------------------------|---------------|
| POST   | `/auth/signup`          | Register a new user, sends OTP    | No            |
| POST   | `/auth/verify-otp`      | Verify OTP and activate account   | No            |   
| POST   | `/auth/resend-otp`      | Resend a new OTP (if expired)     | No            |
| POST   | `/auth/login`           | Login, returns JWT access token   | No            |
| POST   | `/auth/forgot-password` | Request password reset email      | No            |
| POST   | `/auth/reset-password`  | Set new password with reset token | No            |

### Sessions — `/sessions`

| Method | Endpoint                         | Description                                | Auth Required |
|--------|----------------------------------|--------------------------------------------|---------------|
| POST   | `/sessions`                      | Create a new chat session                  | Yes           |
| GET    | `/sessions`                      | List all sessions for current user         | Yes           |
| GET    | `/sessions/{thread_id}`          | Get a single session's metadata and title  | Yes           |
| POST   | `/sessions/{thread_id}/continue` | Mark session as active (touch timestamp)   | Yes           |
| DELETE | `/sessions/{thread_id}`          | Delete session + its LangGraph checkpoint  | Yes           |

### Chat — `/chat`

| Method | Endpoint            | Description                                              | Auth Required |
|--------|---------------------|----------------------------------------------------------|---------------|
| POST   | `/chat`             | Send a message to the agent, generate title if untitled  | Yes           |
| GET    | `/chat/{thread_id}` | Retrieve full conversation history and tool call details | Yes           |

---

## 🔐 Security Notes

- **Password Security**: Passwords are securely hashed with **Argon2** (via `pwdlib`).
- **OTP Validation**: 6-digit OTPs are hashed before database storage, expire after **5 minutes**, and are capped at **5 attempts** before invalidation.
- **Password Reset Protection**: Reset tokens are cryptographically random, single-use, hashed in storage, and expired automatically.
- **Account Enumeration Defense**: The forgot-password endpoint returns identical successful responses regardless of whether the email exists.
- **Route Authorization**: All protected endpoints enforce JWT authentication via FastAPI's `Depends(get_current_user_id)` dependency.
- **Untrusted Prompt Safety**: System prompts for title generation treat user message content as untrusted input to mitigate prompt injection.
