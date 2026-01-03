"""
Victim Chatbot Application - FastAPI Entry Point

This application demonstrates a realistic AI-powered chatbot that uses
AWS Bedrock AgentCore for CSV analysis. It is INTENTIONALLY VULNERABLE
to prompt injection attacks for security research purposes.

VULNERABILITY: User input (including CSV content) is passed directly to
the Code Interpreter without sanitization, enabling prompt injection.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers import chat, analyze
from app.config import get_settings

# Get settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Victim Chatbot Application")
    logger.info(f"Code Interpreter ID: {settings.code_interpreter_id or 'NOT SET'}")
    yield
    logger.info("Shutting down Victim Chatbot Application")


app = FastAPI(
    title="AI Data Analyst",
    description="Upload CSV files for AI-powered analysis. (Demo application for security research)",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(chat.router)
app.include_router(analyze.router)

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
async def health_check():
    """Health check endpoint for ALB."""
    return {
        "status": "healthy",
        "service": "victim-chatbot",
        "code_interpreter": settings.code_interpreter_id or "not-configured"
    }


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "AI Data Analyst"
        }
    )


@app.get("/info")
async def info():
    """Return application info (useful for reconnaissance)."""
    return {
        "application": "AI Data Analyst",
        "version": "1.0.0",
        "backend": "AWS Bedrock AgentCore",
        "features": [
            "CSV file analysis",
            "Natural language queries",
            "Python code execution"
        ],
        "endpoints": {
            "chat": "/chat/",
            "analyze_csv": "/analyze/csv"
        }
    }
