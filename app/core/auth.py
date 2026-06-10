# app/core/auth.py
import logging
from datetime import datetime, timedelta, timezone
import jwt, logging
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from fastapi import Request, Depends, Response, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from datetime import datetime


from app.schemas.auth import TokenUser, LoginResponseModel, UserCreateRead
from app.core.config import settings, BaseSettings
from app.db.models import User, UserRole
from app.errors import UnAuthenticated, UserNotFound, InvalidToken


# passwd_context = CryptContext(schemes=["bcrypt"])

passwd_context = CryptContext(
    # include common schemes to allow verification of hashes created with
    # different algorithms (helps during migrations or mixed-format DBs)
    schemes=["bcrypt_sha256", "bcrypt", "pbkdf2_sha256"],
    deprecated="auto"
)




ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300
logger = logging.getLogger(__name__)


class OptionalOAuth2Scheme(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            return await super().__call__(request)
        except Exception:
            return None

# Replace with the optional version
# optional_oauth2_scheme = OptionalOAuth2Scheme(tokenUrl="token")
optional_oauth2_scheme = OptionalOAuth2Scheme(tokenUrl="/auth/login")

def generate_passwd_hash(password: str) -> str:
    hash = passwd_context.hash(password)

    return hash


def verify_password(password: str, hash: str) -> bool:
    try:
        return passwd_context.verify(password, hash)
    except (UnknownHashError, ValueError) as e:
        # Hash format not recognized by CryptContext OR backend rejected input
        # (e.g., bcrypt backend raising ValueError for >72-byte secrets).
        try:
            redacted = f"{hash[:6]}...len={len(hash)}"
        except Exception:
            redacted = "<unavailable>"
        logger.warning("Password verification failed (%s) for user (sample=%s)", type(e).__name__, redacted)
        return False

def get_password_hash(password: str):
    return passwd_context.hash(password)


def decode_token(token: str, settings: BaseSettings) -> dict:
    try:
        # if isinstance(token, str):
#         #     token = token.encode("utf-8")
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired. Please login again."}
    except jwt.InvalidTokenError:
        raise UnAuthenticated("Invalid authentication token.")
    

def create_access_token(user, expires_delta: timedelta | None = None):
    # Avoid triggering async lazy-loads on detached/expired ORM objects.
    user_dict = getattr(user, "__dict__", {}) if user is not None else {}
    user_id = user_dict.get("id", getattr(user, "id", None))
    user_email = user_dict.get("email", getattr(user, "email", None))
    user_verified = user_dict.get("is_verified", getattr(user, "is_verified", False))
    user_full_name = user_dict.get("full_name", getattr(user, "full_name", None))
    user_role = user_dict.get("role", getattr(user, "role", None))

    if isinstance(user_role, UserRole):
        user_role = user_role.value

    to_encode = {
        "sub": user_email,
        "id": str(user_id),
        "is_verified": user_verified,
        "full_name": user_full_name,
        "role": user_role,
        "exp": datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)



def get_current_user_dependency(settings: BaseSettings):
    def get_current_user(
        request: Request,
        token: Optional[str] = Depends(optional_oauth2_scheme),
    ) -> TokenUser:

        
        campustalk_access_token = token or request.cookies.get("campustalk_access_token")

        if not campustalk_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authenticated. Please login to continue",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = decode_token(campustalk_access_token, settings)
        email = payload.get("sub")
        user_id = payload.get("id")
        full_name = payload.get("full_name")
        role = payload.get("role")

        if not email or not user_id:
            raise UserNotFound()

        return TokenUser(
            full_name=full_name,
            email=email,
            id=user_id,
            is_verified=payload.get("is_verified"),
            role=role,
            campustalk_access_token=campustalk_access_token,
            token_type="bearer"
        )

    return get_current_user



def verify_email_response(user, campustalk_access_token: str, response: Response):

    print("This is the user", user)

    response.set_cookie(
        key="campustalk_access_token",
        value=campustalk_access_token,
        httponly=True, 
        max_age=18000, 
        samesite="none",
        secure=True,
    )

    # Return token and user info in response
    return LoginResponseModel(
        status=True,
        message="User successfully logged in",
        data=TokenUser(
            full_name=getattr(user, "full_name", None),
            email=getattr(user, "email", None),
            id=str(getattr(user, "id", "")),
            is_verified=getattr(user, "is_verified", False),
            role=str(getattr(user, "role", None)),
            campustalk_access_token=campustalk_access_token,
            token_type="bearer"
        )
    )




def get_optional_current_user_dependency(settings):
    def optional_dependency(
        request: Request,
        token: Optional[str] = Depends(optional_oauth2_scheme)
    ) -> Optional[TokenUser]:
        campustalk_access_token = token or request.cookies.get("campustalk_access_token")
        if not campustalk_access_token:
            return None

        try:
            payload = decode_token(campustalk_access_token, settings)
            email = payload.get("sub")
            user_id = payload.get("id")
            full_name = payload.get("full_name")
            role = payload.get("role")

            if not email or not user_id:
                return None

            return TokenUser(
                full_name=full_name,
                email=email,
                id=user_id,
                is_verified=payload.get("is_verified"),
                role=role,
                campustalk_access_token=campustalk_access_token,
                token_type="bearer"
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.PyJWTError:
            return None

    return optional_dependency



def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")



# current_user: Annotated[TokenUser, Depends(get_current_user_dependency(settings=settings))],


# Role-based access control dependencies
def require_role(required_role: UserRole):
    """Dependency factory for requiring a specific user role."""
    def role_checker(current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))) -> User:
        if current_user.role != required_role and current_user.role.value != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires '{required_role.value}' role."
            )
        return current_user
    return role_checker

require_admin = require_role(UserRole.ADMIN)
require_student = require_role(UserRole.STUDENT)
require_institution = require_role(UserRole.INSTITUTION)
