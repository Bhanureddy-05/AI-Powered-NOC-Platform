"""
app/services/reports.py
=======================
Report Generation Service

WHY THIS FILE EXISTS:
    Aggregates metrics and ticket stats over defined date intervals, and
    compiles formatting for CSV downloads and PDF report documents.
"""

import io
import csv
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, cast, Integer

from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.alert import Alert
from app.models.ticket import Ticket

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportService:
    @staticmethod
    async def get_summary_stats(db: AsyncSession, days: int = 7) -> dict:
        """
        Gathers system-wide operations aggregates for the past X days.
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 1. Monitored Devices count
        dev_stmt = select(func.count(Device.id))
        dev_res = await db.execute(dev_stmt)
        total_devices = dev_res.scalar() or 0
        
        # 2. Metrics averages
        metric_stmt = select(
            func.avg(DeviceMetric.cpu_usage),
            func.avg(DeviceMetric.memory_usage),
            func.avg(DeviceMetric.latency),
            func.avg(DeviceMetric.packet_loss)
        ).filter(DeviceMetric.timestamp >= since_date)
        metric_res = await db.execute(metric_stmt)
        avg_cpu, avg_mem, avg_lat, avg_loss = metric_res.first() or (0.0, 0.0, 0.0, 0.0)
        
        # 3. Alert stats
        alert_stmt = select(func.count(Alert.id), func.sum(cast(Alert.resolved, Integer))).filter(Alert.timestamp >= since_date)
        alert_res = await db.execute(alert_stmt)
        total_alerts, resolved_alerts = alert_res.first() or (0, 0)
        total_alerts = total_alerts or 0
        resolved_alerts = resolved_alerts or 0
        
        # 4. Ticket SLA stats
        t_stmt = select(
            func.count(Ticket.id),
            func.sum(cast(Ticket.sla_status == "breached", Integer))
        ).filter(Ticket.created_at >= since_date)
        t_res = await db.execute(t_stmt)
        total_tickets, breached_tickets = t_res.first() or (0, 0)
        total_tickets = total_tickets or 0
        breached_tickets = breached_tickets or 0
        
        sla_compliance = 100.0
        if total_tickets > 0:
            sla_compliance = ((total_tickets - breached_tickets) / total_tickets) * 100.0
            
        return {
            "period_days": days,
            "total_devices": total_devices,
            "average_cpu_usage": round(avg_cpu or 0.0, 2),
            "average_memory_usage": round(avg_mem or 0.0, 2),
            "average_latency_ms": round(avg_lat or 0.0, 2),
            "average_packet_loss_pct": round(avg_loss or 0.0, 2),
            "total_alerts": total_alerts,
            "resolved_alerts_pct": round((resolved_alerts / total_alerts * 100.0) if total_alerts > 0 else 100.0, 1),
            "total_tickets": total_tickets,
            "sla_compliance_pct": round(sla_compliance, 1)
        }

    @staticmethod
    async def export_metrics_csv(db: AsyncSession, days: int = 7) -> str:
        """
        Generates a CSV representation of recent metrics.
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(DeviceMetric, Device.device_name)
            .join(Device, DeviceMetric.device_id == Device.id)
            .filter(DeviceMetric.timestamp >= since_date)
            .order_by(DeviceMetric.timestamp.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(["Timestamp", "Device Name", "CPU Usage (%)", "Memory Usage (%)", "Latency (ms)", "Packet Loss (%)", "Bandwidth (Mbps)", "Anomaly Score", "Anomaly Detected"])
        
        for metric, dev_name in rows:
            writer.writerow([
                metric.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                dev_name,
                metric.cpu_usage,
                metric.memory_usage,
                metric.latency,
                metric.packet_loss,
                metric.bandwidth_usage,
                metric.anomaly_score,
                metric.anomaly_detected
            ])
            
        return output.getvalue()

    @staticmethod
    async def export_alerts_csv(db: AsyncSession, days: int = 7) -> str:
        """
        Generates a CSV export of alert logs.
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(Alert, Device.device_name)
            .join(Device, Alert.device_id == Device.id)
            .filter(Alert.timestamp >= since_date)
            .order_by(Alert.timestamp.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Device Name", "Alert Type", "Severity", "Message", "Status", "Resolved"])
        
        for alert, dev_name in rows:
            writer.writerow([
                alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                dev_name,
                alert.alert_type,
                alert.severity,
                alert.message,
                alert.status,
                alert.resolved
            ])
            
        return output.getvalue()

    @staticmethod
    async def export_tickets_csv(db: AsyncSession, days: int = 7) -> str:
        """
        Generates a CSV export of tickets.
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(Ticket, Device.device_name)
            .join(Device, Ticket.device_id == Device.id)
            .filter(Ticket.created_at >= since_date)
            .order_by(Ticket.created_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ticket ID", "Created At", "Device Name", "Title", "Priority", "Status", "SLA Status", "SLA Deadline"])
        
        for ticket, dev_name in rows:
            writer.writerow([
                ticket.id,
                ticket.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                dev_name,
                ticket.title,
                ticket.priority,
                ticket.status,
                ticket.sla_status,
                ticket.sla_deadline.strftime("%Y-%m-%d %H:%M:%S") if ticket.sla_deadline else ""
            ])
            
        return output.getvalue()

    @staticmethod
    async def generate_pdf_report(db: AsyncSession, days: int = 7) -> bytes:
        """
        Compiles a professional ReportLab PDF summary of NOC operations.
        """
        stats = await ReportService.get_summary_stats(db, days)
        
        # Create output buffer
        pdf_buffer = io.BytesIO()
        
        # Setup document
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        # Load stylesheet
        styles = getSampleStyleSheet()
        
        # Define clean, tailored custom colors (deep slate theme)
        primary_color = colors.HexColor("#0f172a") # Deep Slate
        accent_color = colors.HexColor("#7c3aed")  # Violet
        text_color = colors.HexColor("#334155")    # Slate Gray
        
        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=primary_color,
            spaceAfter=15,
            alignment=0 # Left align
        )
        
        h2_style = ParagraphStyle(
            name="H2Style",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=accent_color,
            spaceBefore=12,
            spaceAfter=8
        )
        
        body_style = ParagraphStyle(
            name="BodyStyle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=text_color,
            spaceAfter=8
        )
        
        story = []
        
        # Header Info
        story.append(Paragraph("AETHER NOC PLATFORM - SUMMARY REPORT", title_style))
        story.append(Paragraph(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style))
        story.append(Paragraph(f"Reporting Period: Past {days} Days", body_style))
        story.append(Spacer(1, 15))
        
        # KPI summary section
        story.append(Paragraph("System Performance Metrics (Averages)", h2_style))
        
        stats_data = [
            ["Monitored Network Assets", str(stats["total_devices"]), "System SLA Compliance", f"{stats['sla_compliance_pct']}%"],
            ["Average CPU Load", f"{stats['average_cpu_usage']}%", "Average Memory Load", f"{stats['average_memory_usage']}%"],
            ["Average Device Latency", f"{stats['average_latency_ms']} ms", "Average Telemetry Loss", f"{stats['average_packet_loss_pct']}%"],
            ["Total Alerts Triggered", str(stats["total_alerts"]), "Resolved Alerts", f"{stats['resolved_alerts_pct']}%"]
        ]
        
        t = Table(stats_data, colWidths=[180, 80, 180, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('TEXTCOLOR', (0,0), (-1,-1), text_color),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")),
            ('BACKGROUND', (2,0), (2,-1), colors.HexColor("#f1f5f9")),
        ]))
        story.append(t)
        story.append(Spacer(1, 20))
        
        # Fetch active critical alerts
        story.append(Paragraph("Recent Unresolved Critical Alerts", h2_style))
        alert_stmt = (
            select(Alert, Device.device_name)
            .join(Device, Alert.device_id == Device.id)
            .filter(Alert.resolved == False)
            .filter(Alert.severity == "critical")
            .order_by(Alert.timestamp.desc())
            .limit(5)
        )
        alert_res = await db.execute(alert_stmt)
        recent_alerts = alert_res.all()
        
        if not recent_alerts:
            story.append(Paragraph("No open critical alerts present.", body_style))
        else:
            alert_table_data = [["Timestamp", "Device Name", "Alert Type", "Message"]]
            for alert, dev_name in recent_alerts:
                alert_table_data.append([
                    alert.timestamp.strftime("%m-%d %H:%M"),
                    dev_name,
                    alert.alert_type,
                    alert.message[:45] + "..." if len(alert.message) > 45 else alert.message
                ])
            alert_table = Table(alert_table_data, colWidths=[90, 100, 100, 230])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), primary_color),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
            ]))
            story.append(alert_table)
            
        story.append(Spacer(1, 20))
        
        # Fetch active incident tickets
        story.append(Paragraph("Open Escalated Tickets", h2_style))
        ticket_stmt = (
            select(Ticket, Device.device_name)
            .join(Device, Ticket.device_id == Device.id)
            .filter(Ticket.status.in_(["open", "assigned", "in_progress", "escalated"]))
            .order_by(Ticket.priority.desc(), Ticket.created_at.asc())
            .limit(5)
        )
        ticket_res = await db.execute(ticket_stmt)
        open_tickets = ticket_res.all()
        
        if not open_tickets:
            story.append(Paragraph("No open escalated tickets present.", body_style))
        else:
            ticket_table_data = [["ID", "Device Name", "Title", "Priority", "Status", "SLA Status"]]
            for ticket, dev_name in open_tickets:
                ticket_table_data.append([
                    ticket.id[:8],
                    dev_name,
                    ticket.title[:30],
                    ticket.priority.upper(),
                    ticket.status.upper(),
                    ticket.sla_status.upper()
                ])
            ticket_table = Table(ticket_table_data, colWidths=[60, 100, 160, 60, 70, 70])
            ticket_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), primary_color),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
            ]))
            story.append(ticket_table)
            
        story.append(Spacer(1, 30))
        story.append(Paragraph("End of Summary Report.", body_style))
        
        # Build document
        doc.build(story)
        
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_bytes
