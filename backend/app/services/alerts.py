"""
app/services/alerts.py
======================
Alert Service Layer

WHY THIS FILE EXISTS:
    Encapsulates backend query building, stats computation, and transactional logic
    governing alert lifecycle states and audit trail logging.
"""

from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from app.models.alert import Alert
from app.models.alert_history import AlertHistory
from app.models.device import Device
from app.models.audit_log import AuditLog
from app.schemas.alert import AlertCreate, AlertUpdate

class AlertService:
    @staticmethod
    async def get_alerts(
        db: AsyncSession,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        device_id: Optional[str] = None,
        page: int = 1,
        size: int = 50
    ) -> Dict:
        """
        Retrieves a paginated list of alerts, filterable by status, severity, and device.
        Joins with the Device table to retrieve device metadata (name, IP).
        """
        # Base query joining Alert and Device
        stmt = select(Alert, Device.device_name, Device.ip_address).join(Device, Alert.device_id == Device.id)
        
        # Apply filters
        if status:
            stmt = stmt.filter(Alert.status == status)
        if severity:
            stmt = stmt.filter(Alert.severity == severity)
        if device_id:
            stmt = stmt.filter(Alert.device_id == device_id)
            
        # Count total matches
        count_stmt = select(func.count(Alert.id))
        if status:
            count_stmt = count_stmt.filter(Alert.status == status)
        if severity:
            count_stmt = count_stmt.filter(Alert.severity == severity)
        if device_id:
            count_stmt = count_stmt.filter(Alert.device_id == device_id)
            
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Apply ordering (newest first) and pagination
        offset = (page - 1) * size
        stmt = stmt.order_by(Alert.timestamp.desc()).offset(offset).limit(size)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        alerts_list = []
        for alert, dev_name, dev_ip in rows:
            # Map SQLAlchemy object fields and add injected device attributes
            alert_dict = {
                "id": alert.id,
                "device_id": alert.device_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
                "status": alert.status,
                "acknowledged_at": alert.acknowledged_at,
                "acknowledged_by": alert.acknowledged_by,
                "resolved_at": alert.resolved_at,
                "resolved_by": alert.resolved_by,
                "device_name": dev_name,
                "device_ip": dev_ip
            }
            alerts_list.append(alert_dict)
            
        pages = (total + size - 1) // size if total > 0 else 1
        
        return {
            "alerts": alerts_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }

    @staticmethod
    async def get_alert_by_id(db: AsyncSession, alert_id: str) -> Optional[Alert]:
        """
        Gets a single alert by UUID.
        """
        result = await db.execute(select(Alert).filter(Alert.id == alert_id))
        return result.scalars().first()

    @staticmethod
    async def create_alert(db: AsyncSession, alert_in: AlertCreate) -> Alert:
        """
        Creates a new alert record. Logs the initial transition to alert_history.
        """
        new_alert = Alert(
            device_id=alert_in.device_id,
            alert_type=alert_in.alert_type,
            severity=alert_in.severity,
            message=alert_in.message,
            timestamp=alert_in.timestamp or datetime.utcnow(),
            resolved=alert_in.resolved,
            status=alert_in.status
        )
        db.add(new_alert)
        await db.flush() # Populate the UUID ID
        
        # Log to AlertHistory
        history_entry = AlertHistory(
            alert_id=new_alert.id,
            status_from=None,
            status_to=new_alert.status,
            notes="Alert automatically triggered by ingestion pipeline."
        )
        db.add(history_entry)
        
        return new_alert

    @staticmethod
    async def update_alert_status(
        db: AsyncSession,
        alert_id: str,
        new_status: str,
        user_id: int,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Updates alert status, setting corresponding timestamps/assignees,
        appends alert history record, and creates audit log.
        """
        alert = await AlertService.get_alert_by_id(db, alert_id)
        if not alert:
            return None
            
        old_status = alert.status
        if old_status == new_status:
            return alert # No change
            
        alert.status = new_status
        
        # Update timestamp details based on target lifecycle status
        if new_status == "acknowledged":
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = user_id
        elif new_status == "resolved":
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = user_id
            alert.resolved = True
        elif new_status == "open":
            alert.resolved = False
            
        # Log to AlertHistory
        history_entry = AlertHistory(
            alert_id=alert.id,
            status_from=old_status,
            status_to=new_status,
            changed_by=user_id,
            notes=notes or f"Alert status changed from {old_status} to {new_status}."
        )
        db.add(history_entry)
        
        # Log to AuditLog
        audit = AuditLog(
            user_id=user_id,
            action="alert_status_updated",
            details=f"Alert: {alert.id} ({alert.alert_type}) status changed {old_status} -> {new_status}",
            ip_address="127.0.0.1" # Stubbed or passed from API
        )
        db.add(audit)
        
        await db.commit()
        await db.refresh(alert)
        return alert

    @staticmethod
    async def get_alert_stats(db: AsyncSession) -> Dict:
        """
        Computes count tallies grouped by severity and lifecycle states.
        """
        # Initialize dictionary
        stats = {
            "total": 0,
            "open": 0,
            "acknowledged": 0,
            "investigating": 0,
            "resolved": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        # Query count grouped by status
        status_stmt = select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
        status_res = await db.execute(status_stmt)
        for stat_name, count in status_res.all():
            if stat_name in stats:
                stats[stat_name] = count
                
        # Query count grouped by severity
        severity_stmt = select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
        severity_res = await db.execute(severity_stmt)
        for sev_name, count in severity_res.all():
            sev_key = sev_name.lower()
            # Map warning to medium or check info if needed
            if sev_key == "warning":
                sev_key = "medium"
            elif sev_key == "info":
                sev_key = "low"
            if sev_key in stats:
                stats[sev_key] = count
                
        total_stmt = select(func.count(Alert.id))
        total_res = await db.execute(total_stmt)
        stats["total"] = total_res.scalar() or 0
        
        return stats

    @staticmethod
    async def get_alert_history(db: AsyncSession, alert_id: str) -> List[AlertHistory]:
        """
        Returns history events for a given alert UUID.
        """
        stmt = select(AlertHistory).filter(AlertHistory.alert_id == alert_id).order_by(AlertHistory.changed_at.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())
