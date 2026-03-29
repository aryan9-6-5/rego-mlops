from typing import Annotated, Any, Callable, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.lib.supabase_client import supabase_client

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict[str, Any]:
    """
    Get the current authenticated user from Supabase.
    """
    token = credentials.credentials
    try:
        user_data = supabase_client.verify_token(token)
        # Fetch role from public.users table
        response = (
            supabase_client.client.table("users")
            .select("role")
            .eq("id", user_data["id"])
            .execute()
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User role not found in database."
            )
            
        user_data["role"] = response.data[0]["role"]
        return user_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def require_role(
    allowed_roles: Sequence[str]
) -> Callable[[CurrentUser], dict[str, Any]]:
    """
    Dependency factory to enforce role-based access control.
    """

    def role_checker(user: CurrentUser) -> dict[str, Any]:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{user['role']}' is not authorized for this action. "
                    f"Allowed: {allowed_roles}"
                ),
            )
        return user

    return role_checker
