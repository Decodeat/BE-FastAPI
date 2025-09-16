"""
Main FastAPI application for nutrition label analysis.
Provides API endpoints for analyzing food images and extracting nutrition information.
"""
import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to Python path if running from decodeat directory
# This needs to be done before any decodeat imports
if os.path.basename(os.getcwd()) == "decodeat":
    parent_dir = os.path.dirname(os.getcwd())
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from decodeat.config import settings
from decodeat.api.routes import router as api_router
from decodeat.api.recommendation_routes import recommendation_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(recommendation_router, prefix="/api/v1/recommend")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "nutrition-label-api",
            "version": settings.api_version
        }
    
    return app


# Create the FastAPI application instance
app = create_app()


if __name__ == "__main__":
    import socket
    
    # Check if port is available, if not, find an available one
    def find_available_port(start_port: int = 8000) -> int:
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No available ports found")
    
    try:
        port = settings.port
        # Test if port is available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
    except OSError:
        port = find_available_port(settings.port)
        print(f"Port {settings.port} is busy, using port {port} instead")
    
    print(f"Starting Nutrition Label Analysis API on http://{settings.host}:{port}")
    print(f"API Documentation available at: http://{settings.host}:{port}/docs")
    
    uvicorn.run(
        "decodeat.main:app" if "decodeat" in sys.modules else "main:app",
        host=settings.host,
        port=port,
        reload=settings.debug
    )