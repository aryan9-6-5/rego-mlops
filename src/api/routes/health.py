from fastapi import APIRouter
import z3

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}

@router.get("/z3")
async def z3_health_check() -> dict[str, str]:
    """Check Z3 solver version and health."""
    try:
        ver = z3.get_version_string()
        return {"status": "ok", "z3_version": ver}
    except Exception as e:
        return {"status": "error", "message": str(e)}
