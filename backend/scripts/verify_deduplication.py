import sys
import os
import asyncio
import time
from datetime import datetime, timedelta

# Adjust python path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session
from app.models.device import Device
from app.models.alert import Alert
from app.services.alerts import AlertService
from sqlalchemy import select, delete

async def test_alert_deduplication_and_resolution():
    print("--------------------------------------------------")
    print("STARTING ALERT DEDUPLICATION & RESOLUTION TESTS...")
    print("--------------------------------------------------")
    
    async with async_session() as db:
        # 1. Setup Test Device
        device_name = "TEST_DEDUPLICATOR_NODE"
        # Clean up any leftover test device
        await db.execute(delete(Device).filter(Device.device_name == device_name))
        await db.commit()

        test_device = Device(
            device_name=device_name,
            ip_address="192.168.99.99",
            location="Test Sandbox Lab",
            device_type="server",
            status="active"
        )
        db.add(test_device)
        await db.commit()
        await db.refresh(test_device)
        print(f"[OK] Seeding test device: {test_device.device_name} (ID: {test_device.id})")

        try:
            # 2. Cycle 1: CPU spike (CPU = 95.0) -> Expect alert created
            print("\nEvaluating Cycle 1 (CPU Spike: 95%)...")
            payload = {
                "cpu_usage": 95.0,
                "memory_usage": 50.0,
                "latency": 15.0,
                "packet_loss": 0.0,
                "bandwidth_usage": 10.0,
                "disk_usage": 45.0,
                "reachability": True
            }
            anomaly_res = {"anomaly_detected": False, "anomaly_score": 0.1}

            fired_alerts, resolved_alerts = await AlertService.process_device_alerts(
                db, test_device, payload, anomaly_res
            )
            await db.commit()

            assert len(fired_alerts) == 1, f"Expected 1 fired alert, got {len(fired_alerts)}"
            assert len(resolved_alerts) == 0, f"Expected 0 resolved alerts, got {len(resolved_alerts)}"
            
            fired_alert = fired_alerts[0]
            assert fired_alert.alert_type == "CPU_SPIKE", f"Expected CPU_SPIKE, got {fired_alert.alert_type}"
            assert fired_alert.occurrence_count == 1, f"Expected occurrence_count = 1, got {fired_alert.occurrence_count}"
            assert fired_alert.status == "open", f"Expected status = open, got {fired_alert.status}"
            print(f"[PASS] Cycle 1 alert generated successfully. Status: {fired_alert.status}, Occurrences: {fired_alert.occurrence_count}")

            # Sleep 1.5s to ensure timestamps differ for verification
            print("Sleeping 1.5 seconds to verify last_seen timestamp shift...")
            await asyncio.sleep(1.5)

            # 3. Cycle 2: CPU spike continues (CPU = 97.0) -> Expect existing alert updated
            print("\nEvaluating Cycle 2 (CPU Spike continues: 97%)...")
            payload["cpu_usage"] = 97.0
            fired_alerts_2, resolved_alerts_2 = await AlertService.process_device_alerts(
                db, test_device, payload, anomaly_res
            )
            await db.commit()

            assert len(fired_alerts_2) == 1, f"Expected 1 fired alert, got {len(fired_alerts_2)}"
            assert len(resolved_alerts_2) == 0, f"Expected 0 resolved alerts, got {len(resolved_alerts_2)}"

            updated_alert = fired_alerts_2[0]
            assert updated_alert.id == fired_alert.id, "Expected same alert ID to be updated"
            assert updated_alert.occurrence_count == 2, f"Expected occurrence_count = 2, got {updated_alert.occurrence_count}"
            assert updated_alert.last_seen > updated_alert.first_seen, "Expected last_seen to be updated and later than first_seen"
            print(f"[PASS] Cycle 2 deduplicated successfully. Status: {updated_alert.status}, Occurrences: {updated_alert.occurrence_count}")
            print(f"       First seen: {updated_alert.first_seen}")
            print(f"       Last seen: {updated_alert.last_seen}")

            # 4. Cycle 3: Return to Normal (CPU = 45.0) -> Expect alert auto-resolved
            print("\nEvaluating Cycle 3 (Resource Clear: CPU = 45.0%)...")
            payload["cpu_usage"] = 45.0
            fired_alerts_3, resolved_alerts_3 = await AlertService.process_device_alerts(
                db, test_device, payload, anomaly_res
            )
            await db.commit()

            assert len(fired_alerts_3) == 0, f"Expected 0 fired alerts, got {len(fired_alerts_3)}"
            assert len(resolved_alerts_3) == 1, f"Expected 1 resolved alert, got {len(resolved_alerts_3)}"

            resolved_alert = resolved_alerts_3[0]
            assert resolved_alert.id == fired_alert.id, "Expected same alert ID to be resolved"
            assert resolved_alert.status == "resolved", f"Expected status = resolved, got {resolved_alert.status}"
            assert resolved_alert.resolved is True, "Expected resolved boolean to be True"
            assert resolved_alert.resolved_at is not None, "Expected resolved_at timestamp to be populated"
            print(f"[PASS] Cycle 3 auto-resolved successfully. Status: {resolved_alert.status}, Resolved At: {resolved_alert.resolved_at}")

            # 5. Cycle 4: CPU spike returns (CPU = 99.0) -> Expect NEW alert created
            print("\nEvaluating Cycle 4 (CPU Spike returns: 99%)...")
            payload["cpu_usage"] = 99.0
            fired_alerts_4, resolved_alerts_4 = await AlertService.process_device_alerts(
                db, test_device, payload, anomaly_res
            )
            await db.commit()

            assert len(fired_alerts_4) == 1, f"Expected 1 fired alert, got {len(fired_alerts_4)}"
            assert len(resolved_alerts_4) == 0, f"Expected 0 resolved alerts, got {len(resolved_alerts_4)}"

            new_alert = fired_alerts_4[0]
            assert new_alert.id != fired_alert.id, f"Expected new alert ID, got the same ID: {new_alert.id}"
            assert new_alert.occurrence_count == 1, f"Expected occurrence_count = 1, got {new_alert.occurrence_count}"
            assert new_alert.status == "open", f"Expected status = open, got {new_alert.status}"
            print(f"[PASS] Cycle 4 created new alert successfully after resolution of previous one.")
            print(f"       Old alert ID: {fired_alert.id}")
            print(f"       New alert ID: {new_alert.id}")

            # 6. Check stats and clean up
            print("\nChecking alert statistics aggregation...")
            stats = await AlertService.get_alert_stats(db)
            print(f"Current open alerts count (overall database): {stats['open']}")
            print(f"Current resolved alerts count (overall database): {stats['resolved']}")

        finally:
            print("\nCleaning up test alerts and device...")
            # Delete alerts related to our test device
            await db.execute(delete(Alert).filter(Alert.device_id == test_device.id))
            # Delete test device
            await db.execute(delete(Device).filter(Device.id == test_device.id))
            await db.commit()
            print("[OK] Cleanup complete.")

    print("\n--------------------------------------------------")
    print("ALL DEDUPLICATION AND AUTO-RESOLUTION TESTS PASSED!")
    print("--------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(test_alert_deduplication_and_resolution())
