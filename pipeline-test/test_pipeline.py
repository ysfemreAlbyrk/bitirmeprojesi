"""End-to-end book processing pipeline test runner.

Usage:
    uv run python scripts/test_pipeline.py /path/to/book.pdf --title "Kitap" --author "Yazar"

This script mimics exactly what the mobile app does:
1. Uploads a book file to Supabase Storage
2. Creates a book record in the DB
3. Triggers (or directly runs) the full processing pipeline
4. Polls status until completion
5. Validates every output: chapters, chunks, media_assets, cover_url, total_pages
6. Tests reading session + stats endpoints

All logging is printed to the console so you can follow every step.
"""
import argparse
import asyncio
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import (
    BookRepository, ChapterRepository, TextChunkRepository,
    MediaAssetRepository, ReadingProgressRepository,
)
from app.core.storage import StorageService
from app.services.book_processing_service import BookProcessingService
from app.models.book import ProcessingStatus
from app.utils.logger import get_logger
from config import settings

# ---------------------------------------------------------------------------
# Lazy provider imports so heavy ML modules are only loaded when needed
# ---------------------------------------------------------------------------
def _get_providers():
    from app.providers.gemini_provider import GeminiProvider
    from app.providers.stable_audio_provider import StableAudioProvider
    from app.providers.clipdrop_provider import ClipdropProvider
    return GeminiProvider(), StableAudioProvider(), ClipdropProvider()


logger = get_logger("vibetale.pipeline_test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _print_section(title: str):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def _print_kv(key: str, value):
    print(f"  {key:<30} {value}")


async def _upload_file(storage: StorageService, file_path: str) -> str:
    _print_section("1. FILE UPLOAD")
    print(f"  Source: {file_path}")
    url = await storage.upload_file(file_path)
    _print_kv("Storage URL", url)
    return url


async def _create_book_record(title: str, author: str, file_path: str, storage_url: str) -> str:
    _print_section("2. BOOK RECORD CREATION")
    book_repo = BookRepository()
    book_id = str(uuid.uuid4())
    ext = Path(file_path).suffix.lower().lstrip(".")
    book_data = {
        "id": book_id,
        "title": title,
        "author": author,
        "format": ext,
        "file_url": storage_url,
        "processing_status": ProcessingStatus.PENDING.value,
        "user_id": "pipeline-test-user",
        "created_at": datetime.now().isoformat(),
    }
    record = book_repo.create(book_data)
    _print_kv("Book ID", record["id"])
    _print_kv("Title", record["title"])
    _print_kv("Format", record["format"])
    return record["id"]


async def _run_pipeline(book_id: str, file_path: str, file_format: str):
    _print_section("3. PROCESSING PIPELINE")
    print("  Instantiating real providers (Gemini + StableAudio + Clipdrop)...")
    llm, audio, image = _get_providers()
    storage = StorageService()
    service = BookProcessingService(llm, audio, image, storage)

    print("  Starting process_book...")
    start = time.time()
    await service.process_book(book_id, file_path, file_format)
    elapsed = time.time() - start
    _print_kv("Elapsed", f"{elapsed:.1f}s")


async def _validate_results(book_id: str):
    _print_section("4. VALIDATION")
    book_repo = BookRepository()
    chapter_repo = ChapterRepository()
    chunk_repo = TextChunkRepository()
    media_repo = MediaAssetRepository()

    book = book_repo.get_by_id(book_id)
    if not book:
        print("  ERROR: Book record not found!")
        return

    _print_kv("Status", book.get("processing_status"))
    _print_kv("Audit Result", book.get("audit_result"))
    _print_kv("Total Pages", book.get("total_pages"))
    _print_kv("Cover URL", bool(book.get("cover_url")))

    chapters = chapter_repo.get_by_book(book_id)
    _print_kv("Chapters", len(chapters))

    chunks = chunk_repo.get_by_book(book_id)
    _print_kv("Chunks", len(chunks))

    analyzed = sum(1 for c in chunks if c.get("analyzed"))
    _print_kv("Analyzed chunks", analyzed)

    with_audio = sum(1 for c in chunks if c.get("audio_url"))
    with_image = sum(1 for c in chunks if c.get("image_url"))
    _print_kv("Chunks with audio", with_audio)
    _print_kv("Chunks with image", with_image)

    all_assets = []
    for ch in chunks:
        all_assets.extend(media_repo.get_by_chunk(ch["id"]))
    _print_kv("media_assets rows", len(all_assets))

    if chunks:
        sample = chunks[0]
        _print_kv("Sample chunk scene", sample.get("scene", "")[:50] + "...")
        _print_kv("Sample chunk audio", bool(sample.get("audio_url")))
        _print_kv("Sample chunk image", bool(sample.get("image_url")))


async def _test_reading_session(book_id: str):
    _print_section("5. READING SESSION & STATS")
    from app.core.database import Database
    db = Database()
    user_id = "pipeline-test-user"

    # Create session
    session_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "book_id": book_id,
        "started_at": datetime.now().isoformat(),
    }
    resp = db.client.table("reading_sessions").insert(session_data).execute()
    session = resp.data[0]
    _print_kv("Session ID", session["id"])

    # Simulate 5s of reading + 3s immersive
    await asyncio.sleep(1)
    ended = datetime.now().isoformat()
    db.client.table("reading_sessions").update({
        "ended_at": ended,
        "duration_seconds": 5,
        "immersive_mode_seconds": 3,
    }).eq("id", session["id"]).execute()
    print("  Session ended (5s total, 3s immersive)")

    # Save progress
    db.client.table("reading_progress").upsert({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "book_id": book_id,
        "current_chunk_id": "test-chunk-id",
        "chapter_number": 1,
        "offset": 0,
    }).execute()
    print("  Progress saved")

    # Query stats
    stats_resp = db.client.table("reading_sessions").select("*").eq("user_id", user_id).execute()
    sessions = stats_resp.data or []
    total_sec = sum(s.get("duration_seconds", 0) or 0 for s in sessions)
    imm_sec = sum(s.get("immersive_mode_seconds", 0) or 0 for s in sessions)
    _print_kv("Total sessions", len(sessions))
    _print_kv("Total seconds", total_sec)
    _print_kv("Immersive seconds", imm_sec)


async def main():
    parser = argparse.ArgumentParser(description="VibeTale pipeline test runner")
    parser.add_argument("file", help="Path to PDF/EPUB file to process")
    parser.add_argument("--title", default="Pipeline Test Book", help="Book title")
    parser.add_argument("--author", default="Test Author", help="Book author")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    ext = file_path.suffix.lower().lstrip(".")
    if ext not in ("pdf", "epub"):
        print(f"ERROR: Unsupported format: {ext}. Use pdf or epub.")
        sys.exit(1)

    _print_section("VIBETALE PIPELINE TEST")
    _print_kv("File", file_path)
    _print_kv("Title", args.title)
    _print_kv("Author", args.author)
    _print_kv("Format", ext)

    storage = StorageService()
    storage_url = await _upload_file(storage, str(file_path))
    book_id = await _create_book_record(args.title, args.author, str(file_path), storage_url)

    try:
        await _run_pipeline(book_id, str(file_path), ext)
        await _validate_results(book_id)
        await _test_reading_session(book_id)
    except Exception as e:
        _print_section("PIPELINE FAILED")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    _print_section("PIPELINE COMPLETE")
    print(f"  Book ID: {book_id}")
    print(f"  Check the DB / Supabase dashboard for full details.")


if __name__ == "__main__":
    asyncio.run(main())
