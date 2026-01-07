import requests
from sqlalchemy import select
from core.db import SessionLocal
from models.sql import DocumentChunk
import litellm
from typing import List

def scholar_search(query: str, limit: int = 5) -> str:
    """
    Search for academic papers using Semantic Scholar API.
    
    Args:
        query: The search query string.
        limit: Max number of results (default 5).
        
    Returns:
        A formatted string containing paper details.
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,authors,year,url,citationCount"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return "No papers found."
            
        results = []
        for paper in data["data"]:
            authors = ", ".join([a["name"] for a in paper.get("authors", [])])
            results.append(
                f"Title: {paper.get('title')}\n"
                f"Year: {paper.get('year')}\n"
                f"Authors: {authors}\n"
                f"Citations: {paper.get('citationCount')}\n"
                f"Abstract: {paper.get('abstract')}\n"
                f"URL: {paper.get('url')}\n"
            )
        
        return "\n---\n".join(results)
    
    except Exception as e:
        return f"Error searching papers: {str(e)}"

def knowledge_retriever(query: str) -> str:
    """
    Retrieve relevant information from the local knowledge base (uploaded PDFs).
    
    Args:
        query: The search query.
        
    Returns:
        Relevant content chunks from the knowledge base.
    """
    try:
        # Generate embedding for the query
        response = litellm.embedding(model="text-embedding-3-small", input=[query])
        query_embedding = response['data'][0]['embedding']
        
        db = SessionLocal()
        try:
            # Query pgvector
            chunks = db.scalars(
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(5)
            ).all()
            
            if not chunks:
                return "No relevant information found in the knowledge base."
            
            results = []
            for chunk in chunks:
                results.append(f"Content: {chunk.content}")
                
            return "\n---\n".join(results)
            
        finally:
            db.close()
            
    except Exception as e:
        return f"Error retrieving knowledge: {str(e)}"

def list_available_skills() -> str:
    """
    List all available skills that the agent can use.
    
    Returns:
        A formatted string listing all skills with their descriptions.
    """
    try:
        from skills.manager import skills_manager
        
        skills = skills_manager.list_all_skills()
        
        if not skills:
            return "No skills available."
        
        results = []
        for i, skill in enumerate(skills, 1):
            status = "✓ ACTIVE" if skill["status"] == "active" else "○ Available"
            results.append(
                f"{i}. {skill['name']} [{status}]\n"
                f"   Description: {skill['description']}\n"
                f"   Triggers: {', '.join(skill['triggers'][:3])}"
            )
        
        header = f"Available Skills ({len(skills)}):\n" + "="*50 + "\n\n"
        return header + "\n\n".join(results)
    
    except Exception as e:
        return f"Error listing skills: {str(e)}"

def activate_skill(skill_name: str) -> str:
    """
    Activate a specific skill to use its capabilities.
    
    Args:
        skill_name: Name of the skill to activate.
        
    Returns:
        Status message indicating success or failure.
    """
    try:
        from skills.manager import skills_manager
        
        success = skills_manager.activate_skill(skill_name)
        
        if success:
            skill_info = skills_manager.get_skill_info(skill_name)
            return (
                f"✓ Successfully activated skill: {skill_name}\n\n"
                f"Description: {skill_info['description']}\n\n"
                f"You can now use the capabilities provided by this skill. "
                f"The skill's instructions have been added to your context."
            )
        else:
            return f"✗ Failed to activate skill: {skill_name}. Skill may not exist or failed to load."
    
    except Exception as e:
        return f"Error activating skill: {str(e)}"
