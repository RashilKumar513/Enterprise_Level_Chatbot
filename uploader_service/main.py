from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from shared.auth import verify_credentials
from shared.chroma_manager import ChromaManager
from shared.config import setup_logging
from shared.database import get_all_documents, get_file_data
from uploader_service.auth_deps import require_admin
from uploader_service.delete import remove_document
from uploader_service.ingest import ingest_document
from uploader_service.upload_page import UPLOAD_PAGE

logger = setup_logging(__name__)

app = FastAPI(
    title="DocumentBrain Upload App",
    description="Separate application for uploading and indexing documents.",
    version="1.0.0",
)

chroma = ChromaManager()


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
async def login(body: LoginRequest):
    """Verify credentials against the database before granting access."""
    if not verify_credentials(body.username.strip(), body.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )
    return {"status": "ok", "username": body.username.strip()}


@app.get("/auth/verify")
async def verify_session(admin: str = Depends(require_admin)):
    return {"status": "ok", "username": admin}


@app.get("/", response_class=HTMLResponse)
async def upload_page():
    return UPLOAD_PAGE


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "storage": "sqlite_database",
        "chunks_indexed": chroma.count(),
        "documents_uploaded": len(get_all_documents()),
    }


@app.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    _admin: str = Depends(require_admin),
):
    """Download original file from SQLite database (admin only)."""
    stored = get_file_data(document_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Document not found")

    file_bytes, filename, filetype = stored
    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return Response(
        content=file_bytes,
        media_type=media_types.get(filetype, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/documents")
async def list_documents():
    """Public read — chatbot can poll this for live updates."""
    return {
        "status": "success",
        "count": len(get_all_documents()),
        "documents": get_all_documents(),
    }


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    _admin: str = Depends(require_admin),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        file_bytes = await file.read()
        result = ingest_document(file.filename, file_bytes)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "document_id": result["document_id"],
                "chunks": result["chunks"],
                "file_size": result["file_size"],
                "storage": "sqlite_database",
            },
        )
    except ValueError as exc:
        logger.error("Validation error during upload: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during upload")
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc


@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    _admin: str = Depends(require_admin),
):
    try:
        result = remove_document(document_id)
        return JSONResponse(status_code=200, content=result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Delete failed")
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc
