from starlette.types import Receive
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.email_verification import EmailVerification
from models.password_reset import PasswordResetToken
from models.user import User
from schemas.auth import (SignupRequest, VerifyOTPRequest, LoginRequest, ResetPasswordRequest, ForgotPasswordRequest)
from services.auth_service import (hash_password, verify_password)
from services.email_service import send_otp_email, send_password_reset_email
from services.otp_service import (generate_otp, get_otp_expiration, hash_otp, verify_otp)
from services.jwt_services import create_access_token
from services.auth_dependency import get_current_user_id
from services.password_reset_service import (generate_reset_token, get_reset_token_expiration, hash_reset_token)


router = APIRouter(prefix="/auth", tags=["Authentication"],)

# Database dependency 
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# Signup Endpoint
@router.post('/signup')
async def signup(data: SignupRequest, db: Session=Depends(get_db)):
    # check if the user already exists
    existing_user = (db.query(User).filter((User.username == data.username) | (User.email == data.email)).first())
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email is already registered.",)

    otp = generate_otp()

    verification = EmailVerification(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        otp_hash=hash_otp(otp),
        expires_at=get_otp_expiration()
    )

    db.add(verification)
    db.commit()

    send_otp_email(recipient_email=data.email, otp=otp)
    return {"message": "OTP sent to your email."}   


# OTP Verfication Endpoint
@router.post("/verify-otp")
async def verify_email(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    # verify the email
    verification = (db.query(EmailVerification).filter(EmailVerification.email == data.email).order_by(EmailVerification.created_at.desc()).first())
    if not verification:
        raise HTTPException(status_code=404, detail="No pending verification found.",)

    now = datetime.now(timezone.utc)

    if verification.expires_at < now:
        db.delete(verification)
        db.commit()

        raise HTTPException(status_code=400,detail="OTP has expired.")

    if verification.attempts >= 5:
        db.delete(verification)
        db.commit()

        raise HTTPException(status_code=400,detail="Too many incorrect attempts.",)

    if not verify_otp(data.otp,verification.otp_hash):
        verification.attempts += 1
        db.commit()

        raise HTTPException(status_code=400,detail="Invalid OTP.",)

    user = User(
        username=verification.username,
        email=verification.email,
        password_hash=verification.password_hash,
        is_verified=True,
    )

    db.add(user)
    db.delete(verification)
    db.commit()

    return {"message": "Account created successfully."}


# Login Endpoint
@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db),):
    # Checks whether the user is in database User Table
    user = (db.query(User).filter(User.username == data.username).first())

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.",)

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email is not verified.",)

    if not verify_password(data.password, user.password_hash,):
        raise HTTPException(status_code=401, detail="Invalid username or password.",)

    access_token = create_access_token(user_id=user.id)

    return {"access_token": access_token,"token_type": "bearer",}


# Forget Password Endpoint
@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db),):
    
    user = (db.query(User).filter(User.email == data.email).first())
    
    if not user:
        return {
            "message": (
                "If an account with this email exists, "
                "a password reset link has been sent."
            )
        }

    reset_token = generate_reset_token()    # Generate secure random token

    reset_token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(reset_token),
        expires_at=get_reset_token_expiration(),
    )
    
    db.add(reset_token_record)
    db.commit()

    send_password_reset_email(recipient_email=user.email, reset_token=reset_token)

    return {
        "message": (
            "If an account with this email exists, "
            "a password reset link has been sent."
        )
    }


# Reset Password Endpoint
@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db),):
    token_hash = hash_reset_token(data.token)   # Hash the token received from the user

    # Find the token in the database
    reset_record = (db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first())

    if not reset_record:        # Token does not exist
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.",)

    if reset_record.used:       # Token has already been used
        raise HTTPException(status_code=400, detail="This reset link has already been used.",)

    if reset_record.expires_at < datetime.now(timezone.utc):       # Token has expired
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.",)

    # Find the user associated with this token
    user = (db.query(User).filter(User.id == reset_record.user_id).first())

    if not user:
        raise HTTPException(status_code=400, detail="User account not found.",)

    # Hash and update the new password
    user.password_hash = hash_password(data.password)

    # Make the reset token single-use
    reset_record.used = True

    db.commit()

    return {"message": "Password reset successfully."}