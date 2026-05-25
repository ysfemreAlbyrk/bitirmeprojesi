"""Admin dashboard router for backend monitoring"""
import os
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import settings
from app.core.dependencies import get_database, get_llm_provider, get_audio_provider, get_image_provider
from app.utils.logger import get_logger

logger = get_logger("vibetale")

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="app/templates/admin")


def _verify_admin_key(key: Optional[str] = None, x_admin_key: Optional[str] = None):
    """Simple admin key verification."""
    effective_key = (x_admin_key or key or "").strip()
    if not settings.admin_dashboard_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    if effective_key != settings.admin_dashboard_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
):
    """Render admin dashboard HTML."""
    _verify_admin_key(key, x_admin_key)
    return templates.TemplateResponse("dashboard.html", {"request": request, "key": key or x_admin_key or ""})


@router.get("/api/stats")
async def admin_stats(
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get backend statistics."""
    _verify_admin_key(key, x_admin_key)

    db = get_database()

    # Count books by status
    statuses = ["pending", "processing", "completed", "failed"]
    stats = {}
    for status in statuses:
        try:
            resp = db.client.table("books").select("*").eq("processing_status", status).execute()
            stats[status] = len(resp.data) if resp.data else 0
        except Exception:
            stats[status] = 0

    try:
        resp = db.client.table("books").select("*").execute()
        stats["total_books"] = len(resp.data) if resp.data else 0
    except Exception:
        stats["total_books"] = 0

    try:
        resp = db.client.table("text_chunks").select("*").execute()
        stats["total_chunks"] = len(resp.data) if resp.data else 0
    except Exception:
        stats["total_chunks"] = 0

    try:
        resp = db.client.table("reading_sessions").select("*").execute()
        stats["total_sessions"] = len(resp.data) if resp.data else 0
    except Exception:
        stats["total_sessions"] = 0

    return stats


@router.get("/api/books")
async def admin_books(
    limit: int = Query(10, ge=1, le=50),
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get recent books."""
    _verify_admin_key(key, x_admin_key)

    db = get_database()
    try:
        resp = db.client.table("books").select("*").order("upload_date", desc=True).limit(limit).execute()
        return {"books": resp.data or []}
    except Exception as e:
        logger.error(f"Admin books query failed: {e}")
        return {"books": [], "error": str(e)}


@router.get("/api/health")
async def admin_health(
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get provider and system health status."""
    _verify_admin_key(key, x_admin_key)

    llm = get_llm_provider()
    audio = get_audio_provider()
    image = get_image_provider()

    # Check Supabase
    db = get_database()
    db_ok = False
    try:
        db.client.table("books").select("count").limit(1).execute()
        db_ok = True
    except Exception:
        pass

    # Check Redis
    redis_ok = False
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "llm_provider": {
            "name": settings.llm_provider,
            "available": llm.is_available()
        },
        "audio_provider": {
            "name": settings.stable_audio_model,
            "available": audio.is_available()
        },
        "image_provider": {
            "name": settings.image_generation_model,
            "available": image.is_available()
        },
        "supabase": {"available": db_ok},
        "redis": {"available": redis_ok},
        "celery_broker": {"available": redis_ok}
    }


@router.get("/api/gpu")
async def admin_gpu(
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get GPU/VRAM usage."""
    _verify_admin_key(key, x_admin_key)

    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            return {
                "available": True,
                "device": torch.cuda.get_device_name(0),
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2),
                "total_gb": round(total, 2),
                "free_gb": round(total - reserved, 2)
            }
        else:
            return {"available": False, "message": "CUDA not available"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@router.get("/api/logs")
async def admin_logs(
    lines: int = Query(50, ge=1, le=200),
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get recent log lines."""
    _verify_admin_key(key, x_admin_key)

    log_dir = Path(settings.log_dir)
    main_log = log_dir / "vibetale.log"
    error_log = log_dir / "vibetale_error.log"

    result = {"main": [], "errors": []}

    try:
        if main_log.exists():
            with open(main_log, "r", encoding="utf-8") as f:
                result["main"] = f.readlines()[-lines:]
    except Exception as e:
        result["main_error"] = str(e)

    try:
        if error_log.exists():
            with open(error_log, "r", encoding="utf-8") as f:
                result["errors"] = f.readlines()[-lines:]
    except Exception as e:
        result["error_log_error"] = str(e)

    return result
