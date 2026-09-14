import requests


BASE_URL = "http://127.0.0.1:8000"


# Sends the login request to /auth/login Endpoint
def login(username: str, password: str):
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    return response


# Creates the session using /sessions Endpoint
def create_session(token: str):
    return requests.post(
        f"{BASE_URL}/sessions",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )


# Gets the List of Sessions for the Current User using /sessions Endpoint
def get_sessions(token: str):
    return requests.get(
        f"{BASE_URL}/sessions",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )


# Resumes the Previous Session using /sessions/{thread_id}/continue Endpoint
def continue_session(token: str, thread_id: str,):
    return requests.post(
        f"{BASE_URL}/sessions/{thread_id}/continue",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )


# Deletes the Specific Session using /sessions/{thread_id} Endpoint
def delete_session(token: str, thread_id: str,):
    return requests.delete(
        f"{BASE_URL}/sessions/{thread_id}",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )


# Sends the user message to the agent using /chat Endpoint
def send_message(token: str, thread_id: str, user_input: str,):
    return requests.post(
        f"{BASE_URL}/chat",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "thread_id": thread_id,
            "user_input": user_input,
        },
    )


# Gets the History of Messages for the Current Session using /chat/{thread_id} Endpoint
def get_chat_history(token: str,thread_id: str,):

    return requests.get(
        f"{BASE_URL}/chat/{thread_id}",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )


# Signs Up a New User using /auth/signup Endpoint
def signup(username: str, email: str, password: str):
    return requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )


# Sends OTP to the Registered Email Address for the New User using /auth/verify-otp Endpoint
def verify_otp(email: str, otp: str):
    return requests.post(
        f"{BASE_URL}/auth/verify-otp",
        json={
            "email": email,
            "otp": otp,
        },
    )


# Sends Forgot Password Request to /auth/forgot-password Endpoint
def forgot_password(email: str):
    return requests.post(
        f"{BASE_URL}/auth/forgot-password",
        json={
            "email": email,
        },
    )


# Resets the User's Password using /auth/reset-password Endpoint
def reset_password(token: str, password: str):
    return requests.post(
        f"{BASE_URL}/auth/reset-password",
        json={
            "token": token,
            "password": password,
        },
    )