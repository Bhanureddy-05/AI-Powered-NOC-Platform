"""
scripts/seed_db.py
==================
Populates the database with initial standard users, core network devices, alerts, and tickets.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Adjust python path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import get_password_hash

from app.db.session import async_session, engine
from app.models.user import User
from app.models.device import Device
from app.models.alert import Alert
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog

async def seed_data():
    print("[SEEDER] Bootstrapping NOC inventory seeder...")
    
    async with async_session() as session:
        # 1. Create Default Users if they don't exist
        print("  Seeding user roles...")
        
        # Admin user
        admin_pass = get_password_hash("AdminSecurePassword123!")
        admin_user = User(
            username="admin",
            email="admin@aethernoc.net",
            hashed_password=admin_pass,
            role="admin",
            created_at=datetime.utcnow()
        )
        session.add(admin_user)
        
        # Operator user
        operator_pass = get_password_hash("OperatorSecurePassword123!")
        operator_user = User(
            username="operator",
            email="operator@aethernoc.net",
            hashed_password=operator_pass,
            role="operator",
            created_at=datetime.utcnow()
        )
        session.add(operator_user)

        # 2. Create Core NOC Devices
        print("  Seeding active network devices...")
        devices = [
            Device(
                device_name="core-router-01",
                ip_address="10.10.1.1",
                location="London HQ - Rack A",
                device_type="router",
                status="active"
            ),
            Device(
                device_name="edge-firewall-01",
                ip_address="10.10.1.254",
                location="London HQ - DMZ Edge",
                device_type="firewall",
                status="active"
            ),
            Device(
                device_name="distribution-switch-01",
                ip_address="10.10.2.1",
                location="London HQ - Floor 1 Cab",
                device_type="switch",
                status="active"
            ),
            Device(
                device_name="app-server-01",
                ip_address="10.10.5.10",
                location="Staging AWS Lab",
                device_type="server",
                status="active"
            )
        ]
        
        for dev in devices:
            session.add(dev)
            
        await session.flush()  # Flush to populate device IDs

        # 3. Create Default Alerts
        print("  Seeding active alerts...")
        alerts = [
            Alert(
                device_id=devices[0].id,
                alert_type="LATENCY_SPIKE",
                severity="critical",
                message="Latency exceeds 150ms target (current: 182ms). Packet loss 1.2%.",
                status="open",
                resolved=False,
                timestamp=datetime.utcnow() - timedelta(minutes=20)
            ),
            Alert(
                device_id=devices[1].id,
                alert_type="SECURITY_BREACH",
                severity="high",
                message="Repeated AAA SSH authentication failures logged from source IP 192.168.100.45",
                status="investigating",
                resolved=False,
                timestamp=datetime.utcnow() - timedelta(hours=2)
            ),
            Alert(
                device_id=devices[3].id,
                alert_type="CPU_HIGH",
                severity="medium",
                message="CPU utilization is at 91.4% sustained over 10 minutes.",
                status="open",
                resolved=False,
                timestamp=datetime.utcnow() - timedelta(minutes=45)
            )
        ]
        
        for alert in alerts:
            session.add(alert)
            
        await session.flush()

        # 4. Create Incident Ticket for critical alert
        print("  Seeding incident ticket tracker...")
        ticket = Ticket(
            device_id=devices[0].id,
            alert_id=alerts[0].id,
            title="CRITICAL: Sustained loopback latency spike on core-router-01",
            description="Automated telemetry flagged Loopback0 latency exceeding 150ms threshold. Traces indicate transit hop drop at carrier level.",
            priority="critical",
            severity="critical",
            status="open",
            created_at=datetime.utcnow() - timedelta(minutes=15),
            updated_at=datetime.utcnow() - timedelta(minutes=15)
        )
        session.add(ticket)

        # 5. Log audit trail entry
        audit = AuditLog(
            user_id=None,
            action="SYSTEM_BOOTSTRAP",
            details="Initial database seeding sequence executed successfully. Admin account and core network devices registered.",
            timestamp=datetime.utcnow()
        )
        session.add(audit)

        await session.commit()
        print("[SUCCESS] Seeding complete! Standard administrator credentials generated:")
        print("  Username: admin")
        print("  Password: AdminSecurePassword123!")
        
if __name__ == "__main__":
    asyncio.run(seed_data())
