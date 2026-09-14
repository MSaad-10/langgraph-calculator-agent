from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.jwt_services import decode_access_token


security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security),) -> int:

    token = credentials.credentials

    try:
        user_id = decode_access_token(token)
        return user_id

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.",)