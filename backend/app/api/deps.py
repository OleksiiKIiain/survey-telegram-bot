import hashlib
import hmac

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.admin import Admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_bot_access(x_bot_key: str = Header(default="")) -> None:
    if not settings.telegram_bot_token or settings.telegram_bot_token.startswith("put-your"):
        raise HTTPException(status_code=503, detail="Bot access is not configured")
    expected = hashlib.sha256(settings.telegram_bot_token.encode()).hexdigest()
    if not hmac.compare_digest(x_bot_key, expected):
        raise HTTPException(status_code=401, detail="Invalid bot credentials")


def get_current_admin(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        admin_id = payload.get("sub")
        if not isinstance(admin_id, str) or not admin_id.isdecimal():
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc
    admin = db.get(Admin, int(admin_id))
    if not admin or not admin.is_active:
        raise credentials_exception
    return admin
