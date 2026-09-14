import streamlit as st
from api import (create_session, send_message, continue_session, delete_session, get_chat_history, get_sessions)


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

        with st.chat_message(
            message["role"]
        ):
            st.write(message["content"])

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

            with st.chat_message("assistant"):
                st.write(assistant_message)

            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": assistant_message,
                }
            )

        else:

            try:
                error = response.json()["detail"]
            except Exception:
                error = "Something went wrong."

            st.error(error)


