import logging
from typing import Annotated, Any, Callable, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.lib.supabase_client import supabase_client

logger = logging.getLogger(__name__)

# auto_error=False so a missing or malformed header is a 401 (FastAPI would
# otherwise answer 403).
security = HTTPBearer(auto_error=False)

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict[str, Any]:
    """The authenticated Supabase user, with the role from the `users` table.

    Every failure is the same 401 with no detail, so the response says nothing
    about why (unknown token, missing profile, backend error). Details go to
    the log, never the client or a user identifier.
    """
    if credentials is None:
        raise UNAUTHORIZED
    try:
        user_data = supabase_client.verify_token(credentials.credentials)
        response = (
            supabase_client.client.table("users")
            .select("role")
            .eq("id", user_data["id"])
            .execute()
        )
        rows = response.data
        if not rows or not isinstance(rows, list):
            logger.warning("Authenticated user has no role profile")
            raise UNAUTHORIZED
        role_data = rows[0]
        if not isinstance(role_data, dict) or "role" not in role_data:
            logger.error("Role profile has an unexpected shape")
            raise UNAUTHORIZED
        user_data["role"] = str(role_data["role"])
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Credential check failed error=%s", type(e).__name__)
        raise UNAUTHORIZED from e


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def require_role(
    allowed_roles: Sequence[str],
) -> Callable[[CurrentUser], dict[str, Any]]:
    """Dependency factory for role-based access control."""

    def role_checker(user: CurrentUser) -> dict[str, Any]:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not allowed to do this.",
            )
        return user

    return role_checker
