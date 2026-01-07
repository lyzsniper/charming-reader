from markitdown import MarkItDown
import litellm
from sqlalchemy.orm import Session
from models.sql import Document, DocumentChunk
from core.config import settings
import os

md = MarkItDown()

def convert_to_markdown(file_path: str) -> str:
    """
    Convert PDF to Markdown using MarkItDown.
    """
    result = md.convert(file_path)
    return result.text_content

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Simple recursive character chunking (or just character count for MVP).
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def generate_embeddings(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """
    Generate embeddings using LiteLLM.
    """
    response = litellm.embedding(model=model, input=texts)
    return [d['embedding'] for d in response['data']]

def process_pdf(file_path: str, db: Session):
    """
    Full pipeline: Convert -> Chunk -> Embed -> Store
    """
    # 1. Create Document record
    filename = os.path.basename(file_path)
    doc_record = Document(filename=filename, is_processed=False)
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    try:
        # 2. Convert to Markdown
        markdown_text = convert_to_markdown(file_path)
        doc_record.content_markdown = markdown_text
        
        # 3. Chunk
        chunks = chunk_text(markdown_text)
        
        # 4. Embed
        # Process in batches to avoid API limits
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            embeddings = generate_embeddings(batch_chunks)
            
            # 5. Store
            for chunk_text_content, embedding in zip(batch_chunks, embeddings):
                chunk_record = DocumentChunk(
                    document_id=doc_record.id,
                    content=chunk_text_content,
                    embedding=embedding,
                    chunk_index=i + batch_chunks.index(chunk_text_content)
                )
                db.add(chunk_record)
        
        doc_record.is_processed = True
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Error processing PDF: {e}")
        # Optionally mark as failed
        raise e

