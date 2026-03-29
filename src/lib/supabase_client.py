import os
from typing import Any

from dotenv import load_dotenv

from supabase import Client, create_client  # type: ignore[attr-defined]

load_dotenv()

class SupabaseClient:
    """Minimal Supabase client wrapper."""

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend admin ops

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")

        self.client: Client = create_client(url, key)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify a Supabase JWT and return the user data."""
        # Supabase Python SDK handles token verification via auth.get_user
        try:
            response = self.client.auth.get_user(token)
            if response and response.user:
                # Convert User object to a dict, including 'id' and other metadata
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "app_metadata": response.user.app_metadata,
                    "user_metadata": response.user.user_metadata,
                }
            raise ValueError("Invalid token: No user found in response")
        except Exception as e:
            raise ValueError(f"Token verification failed: {e}")

supabase_client = SupabaseClient()
