"""Create the two demo accounts on a Supabase project.

    poetry run python scripts/create_demo_users.py

Creates demo-co@rego.dev (compliance officer) and demo-mle@rego.dev (ML engineer)
with the Supabase admin API, and the matching rows in the `users` table that the
API reads roles from. Needs SUPABASE_URL and SUPABASE_SERVICE_KEY.

Passwords: set DEMO_USER_PASSWORD (12+ characters) to choose one for both, or leave
it unset and each account gets its own random password, printed once. Nothing is
stored in the repository. Run it against the project you mean to demo on.
"""

import os
import secrets
import sys
from typing import Any

ACCOUNTS = (
    ("demo-co@rego.dev", "compliance_officer"),
    ("demo-mle@rego.dev", "ml_engineer"),
)
MIN_PASSWORD_LENGTH = 12


def create_accounts(client: Any, shared_password: str | None) -> list[tuple[str, str, str]]:
    """Create each account. Returns (email, role, password)."""
    if shared_password is not None and len(shared_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"DEMO_USER_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters.")
    created = []
    for email, role in ACCOUNTS:
        password = shared_password or secrets.token_urlsafe(16)
        response = client.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"role": role},
            }
        )
        client.table("users").insert(
            {"id": response.user.id, "email": email, "role": role}
        ).execute()
        created.append((email, role, password))
    return created


def main() -> int:
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_KEY"):
        sys.stderr.write("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.\n")
        return 1
    from supabase import create_client  # type: ignore[attr-defined]

    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    try:
        accounts = create_accounts(client, os.environ.get("DEMO_USER_PASSWORD"))
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    for email, role, password in accounts:
        sys.stdout.write(f"{role:<18} {email}  password: {password}\n")
    sys.stdout.write("Keep these somewhere safe. They are not stored anywhere else.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
