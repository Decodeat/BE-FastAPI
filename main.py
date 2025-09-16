"""
Main entry point for the Decodeat FastAPI application.
"""
from decodeat.main import app

if __name__ == "__main__":
    import uvicorn
    from decodeat.config import settings
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )