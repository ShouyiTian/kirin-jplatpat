from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict
import uvicorn
from jplatpat_scraper_async import search_jplatpat_async

app = FastAPI(
    title="J-PlatPat Search API",
    description="API for searching Japanese patent database (J-PlatPat)",
    version="1.0.0"
)


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results to return")
    timeout: int = Field(default=20000, ge=5000, le=60000, description="Timeout in milliseconds")
    fetch_abstract: bool = Field(default=True, description="Whether to fetch abstract (要約) for each patent")
    headless: bool = Field(default=True, description="Run browser in headless mode")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "人工知能",
                "limit": 10,
                "timeout": 20000,
                "fetch_abstract": True,
                "headless": True
            }
        }
    }


class SearchResponse(BaseModel):
    query: str
    message: str
    count: int
    rows: list


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "J-PlatPat Search API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "POST - Search patents",
            "/docs": "GET - API documentation",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/search", response_model=SearchResponse)
async def search_patents(request: SearchRequest):
    """
    Search J-PlatPat database for patents
    
    - **query**: Search query string (required)
    - **limit**: Maximum number of results (1-100, default: 10)
    - **timeout**: Timeout in milliseconds (5000-60000, default: 20000)
    - **fetch_abstract**: Fetch abstract for each patent (default: True)
    - **headless**: Run browser in headless mode (default: True)
    """
    try:
        result = await search_jplatpat_async(
            query=request.query,
            headless=request.headless,
            row_limit=request.limit,
            timeout_ms=request.timeout,
            fetch_abstract=request.fetch_abstract
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
