import shutil
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from rag.ingestion import ingest_file
from rag.engine import get_rag_engine

router = APIRouter(prefix="/rag", tags=["RAG"])

class QueryRequest(BaseModel):
    question: str

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...)
):
    """
    Upload a file (PDF, DOCX, MD, etc.) to be ingested into the RAG system.
    """
    allowed_extensions = {".pdf", ".docx", ".doc", ".md", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".html", ".xml", ".json"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {allowed_extensions}"
        )
    
    upload_dir = "uploads_rag"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        
    # Trigger ingestion in background
    # Note: ingest_file is synchronous for now as LlamaIndex operations can be blocking.
    # We might want to wrap it or make it async in future, but BackgroundTasks works for sync functions too.
    background_tasks.add_task(ingest_file, file_path)
    
    return {"filename": file.filename, "status": "queued_for_ingestion", "path": file_path}

@router.post("/query")
async def query_rag(request: QueryRequest):
    """
    Query the RAG system.
    """
    rag_engine = get_rag_engine()
    
    try:
        # invoke LangGraph
        result = rag_engine.invoke({"question": request.question})
        return {
            "answer": result.get("answer"),
            "source": result.get("source"),
            # "context": result.get("context") # Optional: return context if needed for debugging
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

