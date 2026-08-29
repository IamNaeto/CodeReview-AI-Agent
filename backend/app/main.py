import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.config import settings

app = FastAPI(
    title="Agentic AI Code Review System",
    description="Multi-agent code review system with specialist sub-agents",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api/v1")

# Static files for frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

@app.get("/health")
async def health_check():
    errors = settings.validate()
    if errors:
        return {
            "status": "unhealthy",
            "version": "1.0.0",
            "errors": errors
        }
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/config-status")
async def config_status():
    errors = settings.validate()
    debug = settings.debug_info()
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "debug": debug
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
