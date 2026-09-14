import streamlit as st
from api import (create_session, send_message, continue_session, delete_session, get_chat_history, get_sessions)


TOOL_LABELS = {
    "add":         "➕ Addition",
    "subtract":    "➖ Subtraction",
    "multiply":    "✖️  Multiplication",
    "divide":      "➗ Division",
    "power":       "🔋 Power",
    "modulus":     "🔢 Modulus",
    "square_root": "√  Square Root",
}


def extract_text(content) -> str:
    """Return plain text from either a string or a list of content blocks.

    Live chat messages arrive as a plain string.
    History messages loaded from the DB arrive as a list:
        [{"type": "text", "text": "...", "extras": {...}}, ...]
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
        return ""  # empty list → nothing to show
    return str(content)


def render_message(message: dict):
    """Render a single message, handling tool calls and tool results."""

    role = message.get("role", "")
    content = message.get("content", "")
    tool_calls = message.get("tool_calls", [])

    # ── AI message 
    if role in ("ai", "assistant"):

        # Show tool-call banners when the AI is invoking tools
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc.get("name", "unknown")
                args = tc.get("args", {})
                label = TOOL_LABELS.get(tool_name, f"🔧 {tool_name}")
                args_str = ", ".join(f"{k}={v}" for k, v in args.items())
                with st.chat_message("assistant"):
                    st.info(f"**{label}** — calling `{tool_name}({args_str})`")

        # Show the text reply (skip if empty — that's a pure tool-call trigger)
        text = extract_text(content)
        if text:
            with st.chat_message("assistant"):
                st.write(text)

    # ── Tool result message 
    elif role == "tool":
        pass

    # ── Human message
    elif role in ("human", "user"):
        with st.chat_message("user"):
            st.write(extract_text(content))


def load_sessions():
    response = get_sessions(st.session_state["access_token"])

    if response.status_code == 200:
        return response.json()["sessions"]

    return []


def show_sidebar():

    with st.sidebar:

        st.title("💬 My Chats")

        # New Chat
        if st.button(
            "➕ New Chat",
            use_container_width=True,
        ):

            response = create_session(
                st.session_state["access_token"]
            )

            if response.status_code == 200:

                data = response.json()

                st.session_state["thread_id"] = (
                    data["thread_id"]
                )

                st.session_state["messages"] = []

                st.rerun()

            else:

                st.error("Failed to create chat.")

        st.divider()

        sessions = load_sessions()

        st.subheader("Recent Chats")

        for session in sessions:

            thread_id = session["thread_id"]

            # Short version for displaying in sidebar
            display_id = thread_id[:8]

            if st.button(
                f"Chat {display_id}",
                key=f"chat_{thread_id}",
                use_container_width=True,
            ):

                response = continue_session(
                    st.session_state["access_token"],
                    thread_id,
                )

                if response.status_code == 200:

                    st.session_state["thread_id"] = (
                        thread_id
                    )

                    # Load previous messages
                    history_response = get_chat_history(
                        st.session_state["access_token"],
                        thread_id,
                    )

                    if history_response.status_code == 200:

                        history = (
                            history_response.json()
                        )

                        st.session_state["messages"] = (
                            history["messages"]
                        )

                    else:

                        st.session_state["messages"] = []

                    st.rerun()

        st.divider()

        if st.button(
            "🗑️ Delete Current Chat",
            use_container_width=True,
        ):

            thread_id = st.session_state.get(
                "thread_id"
            )

            if thread_id:

                response = delete_session(
                    st.session_state["access_token"],
                    thread_id,
                )

                if response.status_code == 200:

                    st.session_state["thread_id"] = None
                    st.session_state["messages"] = []

                    st.rerun()


def show_chat():

    show_sidebar()

    st.title("🧮 Calculator Agent")

    st.write(
        f"Welcome, {st.session_state['username']}!"
    )

    if st.button("Logout"):

        st.session_state.clear()
        st.rerun()

    st.divider()

    # Make sure messages exists
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display conversation
    for message in st.session_state["messages"]:
        render_message(message)

    # User input
    user_input = st.chat_input(
        "Ask me a calculation..."
    )

    if user_input:

        # Display user message
        with st.chat_message("user"):
            st.write(user_input)

        st.session_state["messages"].append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        # Send to backend
        response = send_message(
            token=st.session_state["access_token"],
            thread_id=st.session_state["thread_id"],
            user_input=user_input,
        )

        if response.status_code == 200:

            data = response.json()

            assistant_message = data["message"]
            tool_calls = data.get("tool_calls", [])

            # Show tool call banners for each tool used
            for tc in tool_calls:
                render_message({
                    "role": "ai",
                    "content": "",
                    "tool_calls": [tc],
                })
                st.session_state["messages"].append({
                    "role": "ai",
                    "content": "",
                    "tool_calls": [tc],
                })

            # Show and store the final assistant reply
            with st.chat_message("assistant"):
                st.write(assistant_message)

            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": assistant_message,
                    "tool_calls": [],
                }
            )

        else:

            try:
                error = response.json()["detail"]
            except Exception:
                error = "Something went wrong."

            st.error(error)