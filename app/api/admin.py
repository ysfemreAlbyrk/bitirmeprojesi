"""Admin dashboard router for backend monitoring"""
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import settings
from app.core.dependencies import get_database, get_llm_provider, get_audio_provider, get_image_provider
from app.core.storage import StorageService
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
    return templates.TemplateResponse(request, "dashboard.html", {"key": key or x_admin_key or ""})


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

    try:
        resp = db.client.table("users").select("*").execute()
        stats["total_users"] = len(resp.data) if resp.data else 0
    except Exception:
        stats["total_users"] = 0

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
        "celery_broker": {"available": redis_ok, "workers_online": _celery_worker_count()}
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


@router.get("/api/book/{book_id}")
async def admin_book_detail(
    book_id: str,
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get detailed book info with chapters and media."""
    _verify_admin_key(key, x_admin_key)

    db = get_database()
    try:
        book_resp = db.client.table("books").select("*").eq("id", book_id).single().execute()
        book = book_resp.data
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        chapters_resp = db.client.table("chapters").select("*").eq("book_id", book_id).order("chapter_number").execute()
        chunks_resp = db.client.table("text_chunks").select("*").eq("book_id", book_id).order("chunk_index").execute()
        media_resp = db.client.table("media_assets").select("*").eq("book_id", book_id).execute()

        return {
            "book": book,
            "chapters": chapters_resp.data or [],
            "chunks": chunks_resp.data or [],
            "media": media_resp.data or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin book detail failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/book/{book_id}")
async def admin_delete_book(
    book_id: str,
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a book and its related data."""
    _verify_admin_key(key, x_admin_key)

    db = get_database()
    storage = StorageService(db.client)
    try:
        # Get media URLs for cleanup
        media_resp = db.client.table("media_assets").select("*").eq("book_id", book_id).execute()
        media_list = media_resp.data or []

        for media in media_list:
            url = media.get("storage_url", "")
            if url:
                # Extract object name from URL
                parts = url.split("/storage/v1/object/public/media-assets/")
                if len(parts) > 1:
                    object_name = parts[1]
                    try:
                        storage.delete_file(object_name)
                    except Exception as del_err:
                        logger.warning(f"Failed to delete storage file {object_name}: {del_err}")

        # Delete book (cascade will handle chapters, chunks, media, bookmarks)
        db.client.table("books").delete().eq("id", book_id).execute()

        return {"success": True, "message": f"Book {book_id} deleted"}
    except Exception as e:
        logger.error(f"Admin delete book failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/users")
async def admin_users(
    limit: int = Query(20, ge=1, le=100),
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get user list."""
    _verify_admin_key(key, x_admin_key)

    db = get_database()
    try:
        resp = db.client.table("users").select("*").order("created_at", desc=True).limit(limit).execute()
        return {"users": resp.data or []}
    except Exception as e:
        logger.error(f"Admin users query failed: {e}")
        return {"users": [], "error": str(e)}


@router.get("/api/system")
async def admin_system(
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get system metrics (CPU, RAM, disk, uptime)."""
    _verify_admin_key(key, x_admin_key)

    result: Dict[str, Any] = {}

    try:
        import psutil as ps
        result["uptime_seconds"] = int(time.time() - ps.boot_time())
        # CPU
        result["cpu_percent"] = ps.cpu_percent(interval=0.5)
        result["cpu_count"] = ps.cpu_count()
        # RAM
        mem = ps.virtual_memory()
        result["ram"] = {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }
        # Disk
        disk = ps.disk_usage("/")
        result["disk"] = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.used / disk.total * 100, 1),
        }
        # Processes
        result["process_count"] = len(ps.pids())
    except Exception as e:
        result["error"] = str(e)

    return result


def _has_psutil() -> bool:
    try:
        import psutil
        return True
    except ImportError:
        return False


def _celery_worker_count() -> int:
    """Return number of online Celery workers, or 0 if unreachable."""
    try:
        from celery import Celery
        from config import settings
        app = Celery("vibetale", broker=settings.celery_broker_url)
        inspect = app.control.inspect()
        ping = inspect.ping()
        app.close()
        return len(ping) if ping else 0
    except Exception:
        return 0


@router.get("/api/celery")
async def admin_celery(
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get Celery worker status and active tasks."""
    _verify_admin_key(key, x_admin_key)

    result: Dict[str, Any] = {"broker": settings.celery_broker_url, "available": False}

    try:
        from celery import Celery
        app = Celery("vibetale", broker=settings.celery_broker_url)
        inspect = app.control.inspect()

        # Ping workers
        ping = inspect.ping()
        result["workers_online"] = list(ping.keys()) if ping else []
        result["available"] = bool(ping)

        # Active tasks
        active = inspect.active()
        result["active_tasks"] = {}
        if active:
            for worker, tasks in active.items():
                result["active_tasks"][worker] = tasks

        # Scheduled
        scheduled = inspect.scheduled()
        result["scheduled_count"] = sum(len(v) for v in scheduled.values()) if scheduled else 0

        # Registered tasks
        registered = inspect.registered()
        result["registered_tasks"] = {}
        if registered:
            for worker, tasks in registered.items():
                result["registered_tasks"][worker] = tasks

        app.close()
    except Exception as e:
        result["error"] = str(e)

    return result


@router.get("/api/storage")
async def admin_storage(
    key: Optional[str] = Query(None),
    x_admin_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Get storage bucket info and media count."""
    _verify_admin_key(key, x_admin_key)

    db = get_database()
    result: Dict[str, Any] = {}

    try:
        # Count media assets by type
        audio_resp = db.client.table("media_assets").select("count").eq("asset_type", "audio").execute()
        image_resp = db.client.table("media_assets").select("count").eq("asset_type", "image").execute()

        result["audio_count"] = len(audio_resp.data) if audio_resp.data else 0
        result["image_count"] = len(image_resp.data) if image_resp.data else 0
        result["total_media"] = result["audio_count"] + result["image_count"]
        result["bucket"] = "media-assets"
    except Exception as e:
        result["error"] = str(e)

    return result
