from typing import Annotated
from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user():
    """
    Stub for getting the current authenticated user.
    To be implemented in Stage 2.4 with Supabase Auth.
    """
    return {"id": "dummy-user-id", "role": "compliance_officer"}

CurrentUser = Annotated[dict, Depends(get_current_user)]
