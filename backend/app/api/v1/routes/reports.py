"""
app/api/v1/routes/reports.py
============================
Reports & Exports API Router

WHY THIS FILE EXISTS:
    Exposes endpoints for querying summary metrics and downloading formatted PDF/CSV reports.
    Restricts report downloads to Admin and Operator roles.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.db.session import get_db
from app.models.user import User
from app.api.v1.routes.auth import get_current_user, check_role
from app.services.reports import ReportService
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/reports", tags=["Reporting & Exports"])

@router.get("/summary")
async def get_report_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns high-level statistics summary for a given time window (in days).
    """
    return await ReportService.get_summary_stats(db, days)

@router.get("/csv")
async def download_csv_export(
    type: str = Query(..., description="Type of CSV export: metrics, alerts, tickets"),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Downloads raw data records as a CSV spreadsheet stream.
    Requires Admin or Operator permissions.
    """
    csv_type = type.lower()
    
    if csv_type == "metrics":
        csv_data = await ReportService.export_metrics_csv(db, days)
        filename = f"noc_metrics_{days}d.csv"
    elif csv_type == "alerts":
        csv_data = await ReportService.export_alerts_csv(db, days)
        filename = f"noc_alerts_{days}d.csv"
    elif csv_type == "tickets":
        csv_data = await ReportService.export_tickets_csv(db, days)
        filename = f"noc_tickets_{days}d.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export type '{type}'. Must be metrics, alerts, or tickets."
        )
        
    # Generate audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="report_downloaded",
        details=f"Downloaded CSV report. Type: {csv_type}, Period: {days} days",
        ip_address=None
    )
    db.add(audit)
    
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/pdf")
async def download_pdf_report(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Renders and downloads a compiled PDF status report of NOC systems.
    Requires Admin or Operator permissions.
    """
    pdf_bytes = await ReportService.generate_pdf_report(db, days)
    
    # Generate audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="report_downloaded",
        details=f"Downloaded PDF summary report. Period: {days} days",
        ip_address=None
    )
    db.add(audit)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=noc_report_{days}d.pdf",
            "Content-Length": str(len(pdf_bytes))
        }
    )
