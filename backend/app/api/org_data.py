"""Org Data Upload and Management API endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
import io

from ..models.database import get_session
from ..models.models import OrgAnalysis, GradeSalary
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
    - Department (optional)
    - Employee ID (optional)
    - Salary (optional - will use grade configuration if not provided)
    - Work Activities (optional - description of work performed by the role)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV"
        )

    try:
        # Read file content as bytes
        content = await file.read()

        # Pass raw bytes to parser - it handles encoding detection
        csv_content = io.BytesIO(content)

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

        # Auto-import grades from CSV data based on Level
        await _auto_import_grades(result["employees"], db)

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


@router.delete("/clear-all")
async def clear_all_data(db: AsyncSession = Depends(get_session)):
    """
    Clear all org data and analyses to start a new project.

    This removes all uploaded org structures, metrics, and AI analyses.
    API configuration (Claude API key) is preserved.
    """
    # Delete all OrgAnalysis records
    result = await db.execute(select(OrgAnalysis))
    analyses = result.scalars().all()

    deleted_count = len(analyses)

    for analysis in analyses:
        await db.delete(analysis)

    await db.commit()

    return {
        "success": True,
        "message": f"Cleared {deleted_count} analysis record(s). Ready for new project.",
        "deleted_count": deleted_count
    }


async def _auto_import_grades(employees: list, db: AsyncSession):
    """
    Auto-import grades from CSV data based on Level column.

    This ensures grade gap calculations work automatically after CSV upload.
    Grades are ordered by their Level (lower level = higher rank).
    """
    if not employees:
        return

    # Group employees by grade and collect their levels and salaries
    grade_data = {}
    for emp in employees:
        grade = emp.get("grade", "").strip()
        level = emp.get("level", 0)
        salary = emp.get("salary", 0)

        if not grade:
            continue

        if grade not in grade_data:
            grade_data[grade] = {"levels": [], "salaries": []}

        grade_data[grade]["levels"].append(level)
        grade_data[grade]["salaries"].append(salary)

    # Calculate average level and median salary for each grade
    grade_info = []
    for grade, data in grade_data.items():
        avg_level = sum(data["levels"]) / len(data["levels"]) if data["levels"] else 99
        salaries = sorted(data["salaries"])
        median_salary = salaries[len(salaries) // 2] if salaries else 0
        grade_info.append({
            "grade": grade,
            "avg_level": avg_level,
            "median_salary": median_salary
        })

    # Sort by average level (lower level = higher in org = lower display_order)
    grade_info.sort(key=lambda x: x["avg_level"])

    # Import grades into database
    for order, info in enumerate(grade_info, 1):
        # Check if grade already exists
        result = await db.execute(
            select(GradeSalary).where(GradeSalary.grade == info["grade"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Only update salary if CSV provides a non-zero value
            # This preserves standard hierarchy salaries when CSV has no salary column
            if info["median_salary"] > 0:
                existing.median_salary = info["median_salary"]
            # Always update display order based on CSV structure
            existing.display_order = order
        else:
            # Create new grade
            new_grade = GradeSalary(
                grade=info["grade"],
                median_salary=info["median_salary"],
                currency="SGD",
                display_order=order
            )
            db.add(new_grade)

    await db.commit()
