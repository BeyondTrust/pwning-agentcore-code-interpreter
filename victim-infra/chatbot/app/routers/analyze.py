"""
Analyze Router - CSV Analysis Endpoint

Note: This endpoint passes user-controlled CSV content directly into the
LLM prompt without sanitization, making it susceptible to prompt injection.
This is intentional for security research purposes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

from app.services.agentcore import AgentCoreService

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = logging.getLogger(__name__)

# File size limit (50MB)
MAX_CSV_SIZE = 50 * 1024 * 1024

# Initialize service
agentcore_service = AgentCoreService()


class AnalyzeResponse(BaseModel):
    """Response model for analyze endpoint."""
    response: str
    session_id: str
    analysis_complete: bool
    rows_processed: Optional[int] = None


def _run_analysis(user_message: str, csv_text: str, session_id: Optional[str]):
    """Run Code Interpreter analysis in the background."""
    try:
        result = agentcore_service.analyze_csv(
            user_message=user_message,
            csv_content=csv_text,
            session_id=session_id,
        )
        logger.info(f"Background analysis complete for session {result['session_id']}")
    except Exception as e:
        logger.error(f"Background analysis failed: {e}", exc_info=True)


@router.post("/csv", response_model=AnalyzeResponse)
async def analyze_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV file to analyze"),
    message: str = Form("Analyze this data and provide summary statistics", description="Analysis request/question"),
    session_id: Optional[str] = Form(None, description="Optional session ID")
):
    """
    Analyze uploaded CSV file using AI.

    Upload a CSV file and ask questions about the data. The AI will
    analyze the data and provide insights.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are supported"
            )

        # Read CSV content with size limit
        csv_content = await file.read(MAX_CSV_SIZE + 1)
        if len(csv_content) > MAX_CSV_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File too large (max 50MB)"
            )

        try:
            csv_text = csv_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                csv_text = csv_content.decode('latin-1')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to decode CSV file. Please use UTF-8 encoding."
                )

        # Log the request (for demo visibility)
        logger.info(f"CSV analysis request received")
        logger.info(f"  File: {file.filename}")
        logger.info(f"  Size: {len(csv_text)} bytes")
        logger.info(f"  Message: {message[:100]}...")

        # Count rows for response
        rows = csv_text.strip().split('\n')
        row_count = len(rows) - 1  # Exclude header

        # Kick off Code Interpreter in the background so we can return
        # immediately.  The analysis (and any injected payload) keeps
        # running after the HTTP response is sent.
        background_tasks.add_task(_run_analysis, message, csv_text, session_id)

        logger.info(f"Analysis queued for background execution")

        return AnalyzeResponse(
            response="Analysis started. Your data is being processed.",
            session_id=session_id or "pending",
            analysis_complete=False,
            rows_processed=row_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/text")
async def analyze_text(
    data: str = Form(..., description="Raw data to analyze"),
    message: str = Form(..., description="Analysis request/question"),
    session_id: Optional[str] = Form(None)
):
    """
    Analyze raw text data (alternative to CSV upload).

    Accepts raw text data instead of file upload.
    """
    try:
        logger.info(f"Text analysis request: {len(data)} chars")

        result = agentcore_service.analyze_csv(
            user_message=message,
            csv_content=data,
            session_id=session_id
        )

        return AnalyzeResponse(
            response=result["response"],
            session_id=result["session_id"],
            analysis_complete=True
        )

    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
