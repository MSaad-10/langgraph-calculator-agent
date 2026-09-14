import streamlit as st
import time
from api import (login, signup, verify_otp, create_session, get_sessions, forgot_password, reset_password, resend_otp)
from chat import show_chat


st.set_page_config(page_title="Calculator Agent", page_icon="🧮",)


if "page" not in st.session_state:
    st.session_state["page"] = "login"
    

# Show Signup 
def show_signup():
    st.title("🧮 Calculator Agent")
    st.subheader("Create an Account")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password",)

    if st.button("Sign Up", use_container_width=True,):

        if not username or not email or not password:
            st.warning("Please fill in all fields.")

        else:
            response = signup(username, email, password,)

            if response.status_code == 200:
                st.session_state["signup_email"] = email
                st.session_state["signup_username"] = username
                st.session_state["otp_stage"] = True
                st.session_state["otp_expires_at"] = (time.time() + 1*60)
                
                st.success("OTP sent to your email.")

                st.rerun()

            else:

                try:
                    error = response.json()["detail"]
                except Exception:
                    error = "Signup failed."

                st.error(error)

    st.divider()

    if st.button(
        "Already have an account? Sign In"
    ):
        st.session_state["page"] = "login"
        st.rerun()


# Show Login
def show_login():

    st.title("🧮 Calculator Agent")
    st.subheader("Sign In")

    username = st.text_input("Username")

    password = st.text_input(
        "Password",
        type="password",
    )

    if st.button(
        "Sign In",
        use_container_width=True,
    ):

        if not username or not password:

            st.warning(
                "Please enter username and password."
            )

        else:

            response = login(
                username,
                password,
            )

            if response.status_code == 200:

                data = response.json()

                token = data["access_token"]

                st.session_state["access_token"] = token
                st.session_state["username"] = username
                st.session_state["logged_in"] = True

                # Get existing chat sessions
                sessions_response = get_sessions(token)

                if sessions_response.status_code == 200:

                    sessions = (
                        sessions_response
                        .json()["sessions"]
                    )

                    if sessions:

                        # Open the most recent chat
                        st.session_state["thread_id"] = (
                            sessions[0]["thread_id"]
                        )

                    else:

                        # Create the first chat session
                        session_response = create_session(
                            token
                        )

                        if session_response.status_code == 200:

                            session_data = (
                                session_response.json()
                            )

                            st.session_state[
                                "thread_id"
                            ] = session_data["thread_id"]

                st.rerun()

            else:

                try:
                    error = response.json()["detail"]
                except Exception:
                    error = "Login failed."

                st.error(error)

    st.divider()

    # Forgot password
    if st.button(
        "Forgot Password?",
        use_container_width=True,
    ):

        st.session_state["page"] = "forgot_password"

        st.rerun()

    # Sign up
    if st.button(
        "Don't have an account? Sign Up",
        use_container_width=True,
    ):

        st.session_state["page"] = "signup"

        st.rerun()


# Show OTP Verification
def show_otp_verification():

    st.title("📧 Verify Your Email")
    email = st.session_state["signup_email"]

    st.write(f"Enter the 6-digit OTP sent to {email}.")

    # Get OTP expiration time
    expires_at = st.session_state.get("otp_expires_at")

    # Calculate remaining time
    remaining_seconds = 0

    if expires_at:
        remaining_seconds = max(0, int(expires_at - time.time()))

    if remaining_seconds > 0:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        # Live countdown placeholder — updates every second via rerun
        timer_placeholder = st.empty()
        timer_placeholder.info(f"OTP expires in {minutes:02d}:{seconds:02d}")

        otp = st.text_input("OTP", max_chars=6,)

        if st.button("Verify Email", use_container_width=True,):

            if not otp:
                st.warning("Please enter the OTP.")
            else:

                response = verify_otp(email, otp,)

                if response.status_code == 200:
                    st.balloons()
                    st.success("✅ Email verified! Your account has been created successfully.")
                    st.info("Redirecting you to Sign In in a moment...")

                    # Give the user time to read the success message
                    time.sleep(3)

                    st.session_state.pop("signup_email", None,)
                    st.session_state.pop("signup_username", None,)
                    st.session_state.pop("otp_stage", None,)
                    st.session_state.pop("otp_expires_at", None,)

                    st.session_state["page"] = "login"

                    st.rerun()

                else:

                    try:
                        error = response.json()["detail"]

                    except Exception:
                        error = "OTP verification failed."

                    st.error(error)

        # Tick every second to keep the countdown live
        time.sleep(1)
        st.rerun()

    # OTP has expired
    else:

        st.error("Your OTP has expired.")

        if st.button("Resend OTP", use_container_width=True,):

            response = resend_otp(email)

            if response.status_code == 200:

                st.session_state["otp_expires_at"] = (time.time() + 1 * 60)

                st.success("A new OTP has been sent to your email.")

                st.rerun()

            else:

                try:
                    error = response.json()["detail"]

                except Exception:
                    error = "Unable to resend OTP."

                st.error(error)


# Forget Password Screen
def show_forgot_password():

    st.title("🔐 Reset Password")

    st.subheader("Forgot Password?")

    st.write(
        "Enter your registered email address to receive "
        "a password reset link."
    )

    email = st.text_input(
        "Email",
        placeholder="Enter your registered email",
    )

    if st.button(
        "Send Reset Link",
        use_container_width=True,
    ):

        if not email:

            st.warning(
                "Please enter your email address."
            )

        else:

            response = forgot_password(email)

            if response.status_code == 200:

                data = response.json()

                st.success(
                    data.get(
                        "message",
                        "If an account with this email exists, "
                        "a password reset link has been sent.",
                    )
                )

            else:

                try:
                    error = response.json()["detail"]

                except Exception:
                    error = (
                        "Unable to process the password "
                        "reset request."
                    )

                st.error(error)

    st.divider()

    if st.button(
        "← Back to Sign In",
        use_container_width=True,
    ):

        st.session_state["page"] = "login"

        st.rerun()


# Reset Password Screen
def show_reset_password(token: str):

    st.title("🔐 Set New Password")
    st.subheader("Create a new password")
    st.write("Enter your new password below.")

    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Set New Password", use_container_width=True,):

        if not new_password or not confirm_password:
            st.warning("Please fill in both password fields.")

        elif new_password != confirm_password:
            st.error("Passwords do not match.")

        else:
            response = reset_password(token=token, password=new_password,)

            if response.status_code == 200:
                # Clear the URL token so the router doesn't re-enter
                # this screen on the next rerun
                st.query_params.clear()
                st.session_state.pop("reset_link_expired", None)

                st.success("✅ Password reset successfully!")
                st.info("Redirecting you to Sign In in a moment...")

                time.sleep(2.5)

                st.session_state["page"] = "login"
                st.rerun()

            else:
                try:
                    error = response.json()["detail"]
                except Exception:
                    error = "Unable to reset the password."

                st.error(error)

                # Mark the link as failed so the Resend section appears
                st.session_state["reset_link_expired"] = True

    # ── Resend Link section 
    if st.session_state.get("reset_link_expired"):

        st.divider()
        st.warning(
            "Your reset link is expired or invalid. "
            "Enter your email below to receive a new one."
        )

        resend_email = st.text_input(
            "Email address",
            placeholder="Enter your registered email",
            key="resend_reset_email",
        )

        if st.button("📧 Resend Link", use_container_width=True):

            if not resend_email:
                st.warning("Please enter your email address.")

            else:
                resend_response = forgot_password(resend_email)

                if resend_response.status_code == 200:
                    st.session_state.pop("reset_link_expired", None)
                    st.success(
                        "✅ A new password reset link has been sent to your email."
                    )

                else:
                    try:
                        err = resend_response.json()["detail"]
                    except Exception:
                        err = "Unable to send reset link. Please try again."
                    st.error(err)

    st.divider()

    if st.button("← Back to Sign In", use_container_width=True,):
        st.session_state.pop("reset_link_expired", None)
        st.session_state["page"] = "login"
        st.rerun()


query_params = st.query_params

url_page = query_params.get("page") 
reset_token = query_params.get("token") 

# Password reset link from email 

if url_page == "reset-password" and reset_token: show_reset_password(reset_token) 

else:
    if st.session_state.get("logged_in", False):
        show_chat()

    elif st.session_state.get("otp_stage", False):
        show_otp_verification()

    elif st.session_state.get("page", "login") == "signup":
        show_signup()

    elif st.session_state.get("page", "login") == "forgot_password":
        show_forgot_password()

    else:
        show_login()