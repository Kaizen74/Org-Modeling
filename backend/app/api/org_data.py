"""Org Data Upload and Management API endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
import io

from ..models.database import get_session
from ..models.models import OrgAnalysis
from ..parsers.csv_parser import OrgCSVParser

router = APIRouter(prefix="/api/v1/org-data", tags=["org-data"])


class UploadResponse(BaseModel):
    success: bool
    message: str
    employee_count: int
    manager_count: int
    validation_errors: list
    metadata: dict


class OrgDataResponse(BaseModel):
    employees: list
    hierarchy: dict
    metadata: dict


@router.post("/upload-csv", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session)
):
    """
    Upload and parse an org structure CSV file.

    Expected CSV columns:
    - Name (required)
    - Job Title (required)
    - Grade (required)
    - Level (required)
    - Line Manager (required)
    - Salary (required)
    - Department (optional)
    - Employee ID (optional)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV"
        )

    try:
        # Read file content
        content = await file.read()
        csv_content = io.StringIO(content.decode("utf-8"))

        # Parse CSV
        parser = OrgCSVParser(csv_content)
        result = parser.parse()

        if result["validation_errors"] and not result["employees"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "CSV validation failed",
                    "errors": result["validation_errors"]
                }
            )

        # Store parsed data in database
        analysis = OrgAnalysis(
            name=file.filename.replace(".csv", ""),
            employee_count=result["metadata"].get("total_employees", 0),
            raw_data={
                "employees": result["employees"],
                "hierarchy": parser.get_org_hierarchy()
            },
            metrics=None  # Will be calculated separately
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)

        return UploadResponse(
            success=True,
            message=f"Successfully parsed {result['metadata']['total_employees']} employees",
            employee_count=result["metadata"]["total_employees"],
            manager_count=result["metadata"]["manager_count"],
            validation_errors=result["validation_errors"],
            metadata=result["metadata"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process CSV: {str(e)}"
        )


@router.get("/latest", response_model=OrgDataResponse)
async def get_latest_org_data(db: AsyncSession = Depends(get_session)):
    """Get the most recently uploaded org data."""
    result = await db.execute(
        select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No org data found. Please upload a CSV first."
        )

    return OrgDataResponse(
        employees=analysis.raw_data.get("employees", []),
        hierarchy=analysis.raw_data.get("hierarchy", {}),
        metadata={
            "id": analysis.id,
            "name": analysis.name,
            "employee_count": analysis.employee_count,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None
        }
    )


@router.get("/analyses")
async def list_analyses(db: AsyncSession = Depends(get_session)):
    """List all stored org analyses."""
    result = await db.execute(
        select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "employee_count": a.employee_count,
            "has_metrics": a.metrics is not None,
            "has_ai_analysis": a.ai_analysis is not None,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in analyses
    ]


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, db: AsyncSession = Depends(get_session)):
    """Get a specific analysis by ID."""
    result = await db.execute(
        select(OrgAnalysis).where(OrgAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "id": analysis.id,
        "name": analysis.name,
        "employee_count": analysis.employee_count,
        "employees": analysis.raw_data.get("employees", []) if analysis.raw_data else [],
        "hierarchy": analysis.raw_data.get("hierarchy", {}) if analysis.raw_data else {},
        "metrics": analysis.metrics,
        "ai_analysis": analysis.ai_analysis,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None
    }


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str, db: AsyncSession = Depends(get_session)):
    """Delete an analysis."""
    result = await db.execute(
        select(OrgAnalysis).where(OrgAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    await db.delete(analysis)
    await db.commit()
    return {"message": f"Analysis '{analysis.name}' deleted"}
