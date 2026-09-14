from database import engine
from models.user import Base
from models.email_verification import EmailVerification
from models.chat_session import ChatSession
from models.password_reset import PasswordResetToken


Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")