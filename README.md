# Arithma — Calculator Agent

A full-stack AI-powered calculator application built with **LangGraph**, **FastAPI**, and **Vanilla JS**. Arithma is a focused arithmetic assistant that uses a language model to understand natural-language math queries and executes calculations through reliable, deterministic tool calls — never performing arithmetic itself. The application features a complete authentication system with email verification, JWT-based sessions, and multi-turn persistent chat history.

---

## ✨ Features

- 🤖 **LangGraph ReAct Agent** — LLM decides which calculator tool to invoke; results are deterministic
- 🔐 **Full Auth System** — Signup → OTP email verification → Login → JWT access tokens
- 🔑 **Password Reset** — Secure token-based email reset flow
- 💬 **Persistent Chat Sessions** — Every conversation is checkpointed to PostgreSQL via LangGraph
- 📜 **Chat History** — Full message history (human, AI, tool calls) per session
- 🖥️ **Single-Page Frontend** — Vanilla JS SPA with Markdown + KaTeX rendering

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Web Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| AI / Agent | [LangGraph](https://langchain-ai.github.io/langgraph/) + [LangChain](https://python.langchain.com/) |
| LLM | Google Gemini (`gemini-3.5-flash`) via `google-genai` |
| Agent Checkpointing | `langgraph-checkpoint-postgres` (PostgreSQL) |
| ORM | [SQLAlchemy](https://www.sqlalchemy.org/) (v2, mapped columns) |
| Database Driver | `psycopg` / `psycopg-pool` |
| Auth | JWT (`PyJWT`), `pwdlib` (Argon2 password hashing) |
| Email | Python `smtplib` over STARTTLS |
| Validation | [Pydantic](https://docs.pydantic.dev/) v2 |
| Config | `python-dotenv` |

### Frontend
| Layer | Technology |
|---|---|
| Build Tool | [Vite](https://vitejs.dev/) v8 |
| Language | Vanilla JavaScript (ES Modules) |
| Styling | Vanilla CSS |
| Markdown Rendering | [`marked`](https://marked.js.org/) |
| Math Rendering | [`KaTeX`](https://katex.org/) |
| Sanitization | [`DOMPurify`](https://github.com/cure53/DOMPurify) |

### Infrastructure
| Component | Technology |
|---|---|
| Database | PostgreSQL |
| SMTP | Gmail (or any STARTTLS-compatible server) |

---

## 🗂️ Project Architecture

```
calculator_agent/
├── .env.example                       # Template for environment variables
├── .gitignore
├── requirements.txt                   # Python dependencies
│
├── backend/
│   ├── main.py                        # FastAPI app entry point, lifespan, router registration
│   ├── database.py                    # SQLAlchemy engine + SessionLocal factory
│   ├── create_tables.py               # One-time script to create all DB tables
│   │
│   ├── agent/
│   │   ├── agent.py                   # LangGraph StateGraph definition (nodes, edges, router)
│   │   └── tools.py                   # Calculator tools: add, subtract, multiply, divide, power, modulus, sqrt
│   │
│   ├── models/                        # SQLAlchemy ORM table definitions
│   │   ├── user.py                    # users table + Base declarative class
│   │   ├── email_verification.py      # email_verifications table (pre-signup OTP staging)
│   │   ├── chat_session.py            # chat_sessions table (thread_id registry)
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
│       └── password_reset_service.py  # Reset token generation, hashing, expiry
│
└── frontend/
    ├── index.html                     # SPA shell
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.js                    # All frontend logic (routing, auth, chat UI)
        └── style.css                  # All styles
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

> Row is **deleted** and a `users` row is **created** on successful OTP verification.

---

### `chat_sessions`
| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, auto-increment |
| `thread_id` | VARCHAR(100) | UNIQUE, NOT NULL, indexed |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, indexed |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now(), auto-updated |

> `thread_id` is a UUID-v4 string that acts as the key for LangGraph's PostgreSQL checkpointer.

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

> Tokens are single-use. All previous unused tokens are invalidated on each new reset request.

---

### LangGraph Checkpointer Tables (auto-created by LangGraph)
LangGraph creates its own tables in PostgreSQL for persisting agent conversation state (messages, tool call history). These are managed automatically by `checkpointer.setup()` in `main.py` and are keyed by `thread_id`.

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
  ← 200: "OTP sent to your email"

User enters OTP
  → POST /auth/verify-otp
    → Look up `email_verifications` by email (latest row)
    → Check expiry (5 min) and attempt count (max 5)
    → Verify OTP hash
    → On success: INSERT into `users` (is_verified=True)
               + DELETE from `email_verifications`
  ← 200: "Account created successfully"
```

### 2. Login Flow
```
User submits credentials
  → POST /auth/login
    → Query `users` by username
    → Check is_verified == True
    → Verify password hash (Argon2)
    → Create JWT (payload: {sub: user_id, exp: now+60min})
  ← 200: { access_token, token_type: "bearer" }

JWT stored in frontend (localStorage / memory)
  → Attached as: Authorization: Bearer <token>
  → All protected routes use get_current_user_id() dependency
     which decodes JWT → extracts user_id
```

### 3. Chat Flow
```
User creates a session
  → POST /sessions  [JWT required]
    → Generate UUID → thread_id
    → INSERT into `chat_sessions`
  ← 200: { thread_id }

User sends a message
  → POST /chat  [JWT required]
    Body: { thread_id, user_input }
    → Validate thread_id belongs to user in `chat_sessions`
    → Snapshot agent state BEFORE invoke (count existing messages)
    → agent.invoke({ messages: [HumanMessage(user_input)] }, config={thread_id})

        LangGraph Agent Loop:
        ┌─────────────────────────────────────────────────────────┐
        │ START → llm_call                                        │
        │   LLM receives [SystemMessage + all history + new msg]  │
        │   LLM returns: either tool_calls or final text          │
        │                                                         │
        │ if tool_calls → tool_node                               │
        │   Execute each tool (add/subtract/multiply/etc.)        │
        │   Return ToolMessage(result) for each                   │
        │   → loop back to llm_call                               │
        │                                                         │
        │ if no tool_calls → END                                  │
        └─────────────────────────────────────────────────────────┘

    → All messages checkpointed to PostgreSQL automatically
    → Extract only NEW messages from this turn
    → Collect tool_calls made this turn
    → Update chat_sessions.updated_at
  ← 200: { thread_id, message: <final AI text>, tool_calls: [...] }

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

## ⚙️ LangGraph Agent Architecture

The agent is a **ReAct-style** graph built with `StateGraph`:

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
 │ tool_node │  ← Executes the actual arithmetic
 └───────────┘
      │
      └──────────► llm_call  (loop back)
```

**State** (`AgentState`):
- `messages` — Full conversation history (inherited from `MessagesState`)
- `llm_calls` — Counter of LLM invocations in the current turn

**Available Tools:**

| Tool | Operation | Notes |
|---|---|---|
| `add(a, b)` | `a + b` | |
| `subtract(a, b)` | `a - b` | |
| `multiply(a, b)` | `a x b` | |
| `divide(a, b)` | `a / b` | Raises on `b == 0` |
| `power(a, b)` | `a ** b` | Raises on `0 ** negative` |
| `modulus(a, b)` | `a % b` | Raises on `b == 0` |
| `square_root(n)` | `n ** 0.5` | Raises on negative input |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (running locally or remote)
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) enabled
- A [Google AI Studio API Key](https://aistudio.google.com/app/apikey)

---

### 1. Clone the Repository

```bash
git clone https://github.com/MSaad-10/langgraph-calculator-agent.git
cd langgraph-calculator-agent
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

> **Generate a JWT secret key:**
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

# Create the PostgreSQL database first (in psql or pgAdmin):
# CREATE DATABASE calculator_db;

# Create application tables
cd backend
python create_tables.py
```

---

### 4. Run the Backend

```bash
# From the backend/ directory
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

### 5. Set Up and Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 📡 API Reference

### Authentication — `/auth`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/auth/signup` | Register a new user, sends OTP | No |
| POST | `/auth/verify-otp` | Verify OTP and activate account | No |
| POST | `/auth/resend-otp` | Resend a new OTP (if expired) | No |
| POST | `/auth/login` | Login, returns JWT | No |
| POST | `/auth/forgot-password` | Request password reset email | No |
| POST | `/auth/reset-password` | Set new password with reset token | No |

### Sessions — `/sessions`

| Method | Endpoint                         | Description                                | Auth Required |
|--------|----------------------------------|--------------------------------------------|---------------|
| POST   | `/sessions`                      | Create a new chat session                  | Yes           |
| GET    | `/sessions`                      | List all sessions for current user         | Yes           |
| GET    | `/sessions/{thread_id}`          | Get a single session                       | Yes           |
| POST   | `/sessions/{thread_id}/continue` | Mark session as active (touch timestamp)   | Yes           |
| DELETE | `/sessions/{thread_id}`          | Delete session + its LangGraph checkpoint  | Yes           |

### Chat — `/chat`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/chat` | Send a message to the agent | Yes |
| GET | `/chat/{thread_id}` | Retrieve full conversation history | Yes |

---

## 🔐 Security Notes

- Passwords are hashed with **Argon2** (via `pwdlib`)
- OTPs are hashed before storage and expire after **5 minutes**
- OTP attempts are rate-limited to **5 tries** before the record is invalidated
- Password reset tokens are single-use and hashed before storage
- Forgot-password endpoint returns identical responses regardless of email existence (prevents user enumeration)
- JWT tokens are validated on every protected request via a FastAPI `Depends` injection
