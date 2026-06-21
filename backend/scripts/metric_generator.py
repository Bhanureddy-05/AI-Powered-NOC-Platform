"""
scripts/metric_generator.py
===========================
Telemetry Metrics Simulator & Database Seeder

WHY THIS FILE EXISTS:
    In development environments, we don't have live Cisco switches streaming
    gRPC telemetry. This script acts as the network simulator, generating
    structured, realistic time-series performance metrics for all registered devices.
    It supports seeding historical data to instantly populate charts.
"""

import sys
import os
import asyncio
import random
import math
import argparse
from datetime import datetime, timedelta

# Adjust python path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from app.db.session import async_session
from app.models.device import Device
from app.models.metric import DeviceMetric

def generate_telemetry_point(device_type: str, time_offset_hours: float) -> dict:
    """
    Generates a single realistic metric data point.
    Uses sine waves to simulate diurnal traffic curves (peaks during business hours).
    """
    # Diurnal factor: peaks between 9 AM and 5 PM (business hours)
    # math.sin returns a value between -1 and 1
    diurnal_factor = math.sin((time_offset_hours - 6) * (2 * math.pi / 24)) * 0.4 + 0.5  # bounds: [0.1, 0.9]
    
    # Random variance
    noise = random.uniform(-0.05, 0.05)
    activity = max(0.01, min(0.99, diurnal_factor + noise))

    # Device type adjustments
    if device_type.lower() == "router":
        cpu = 15 + (activity * 45)             # 15% - 60% CPU
        memory = 40 + (activity * 15)          # 40% - 55% RAM
        bandwidth = 50 + (activity * 400)      # 50 - 450 Mbps
        latency = 5 + (activity * 15)          # 5 - 20 ms
    elif device_type.lower() == "firewall":
        cpu = 20 + (activity * 60)             # 20% - 80% CPU
        memory = 55 + (activity * 25)          # 55% - 80% RAM
        bandwidth = 100 + (activity * 650)     # 100 - 750 Mbps
        latency = 2 + (activity * 8)           # 2 - 10 ms
    elif device_type.lower() == "switch":
        cpu = 5 + (activity * 25)              # 5% - 30% CPU
        memory = 20 + (activity * 10)          # 20% - 30% RAM
        bandwidth = 200 + (activity * 800)     # 200 - 1000 Mbps
        latency = 1 + (activity * 4)           # 1 - 5 ms
    else:  # server
        cpu = 10 + (activity * 75)             # 10% - 85% CPU
        memory = 30 + (activity * 50)          # 30% - 80% RAM
        bandwidth = 20 + (activity * 300)      # 20 - 320 Mbps
        latency = 3 + (activity * 12)          # 3 - 15 ms

    # Introduce minor packet loss under high activity
    packet_loss = 0.0
    if activity > 0.85:
        # 0.1% to 1.5% packet loss on network spikes
        packet_loss = round(random.uniform(0.1, 1.5), 2)
    elif random.random() > 0.98:
        # Rare random drop
        packet_loss = 0.1

    # Latency spikes (simulates network congestion / routing loops)
    if random.random() > 0.97:
        latency += random.uniform(50, 150)
        
    return {
        "cpu_usage": round(cpu, 1),
        "memory_usage": round(memory, 1),
        "latency": round(latency, 2),
        "packet_loss": packet_loss,
        "bandwidth_usage": round(bandwidth, 2)
    }

async def seed_historical_metrics(db_session, devices, hours=24):
    """
    Seeds historical metrics spaced every 5 minutes in the past.
    """
    print(f"[SEEDER] Seeding {hours} hours of telemetry data for {len(devices)} devices...")
    total_inserted = 0
    now = datetime.utcnow()
    
    # 5-minute increments -> 12 points per hour
    intervals = int((hours * 60) / 5)
    
    for device in devices:
        print(f"  Generating seed records for device: {device.device_name}...")
        for i in range(intervals):
            # Calculate back in time
            time_offset = i * 5  # minutes
            timestamp = now - timedelta(minutes=time_offset)
            
            # Determine time-of-day offsets for the sine wave simulator
            time_offset_hours = timestamp.hour + (timestamp.minute / 60.0)
            
            payload = generate_telemetry_point(device.device_type, time_offset_hours)
            
            metric = DeviceMetric(
                device_id=device.id,
                cpu_usage=payload["cpu_usage"],
                memory_usage=payload["memory_usage"],
                latency=payload["latency"],
                packet_loss=payload["packet_loss"],
                bandwidth_usage=payload["bandwidth_usage"],
                anomaly_score=0.0,
                anomaly_detected=False,
                timestamp=timestamp
            )
            db_session.add(metric)
            total_inserted += 1
            
            # Commit periodically to keep transaction sizes manageable
            if total_inserted % 500 == 0:
                await db_session.commit()
                
    await db_session.commit()
    print(f"[SEEDER] Successfully seeded {total_inserted} telemetry database records!")

async def run_live_simulation(interval_seconds=5):
    """
    Performs periodic telemetry generation in a continuous loop.
    """
    print(f"[SIMULATOR] Starting live simulation loop. Sending metrics every {interval_seconds}s...")
    
    while True:
        try:
            async with async_session() as session:
                # Query active devices
                result = await session.execute(select(Device).filter(Device.status == "active"))
                devices = result.scalars().all()
                
                if not devices:
                    print("[SIMULATOR] Warning: No active devices found in inventory. Register some devices first.")
                else:
                    now = datetime.utcnow()
                    time_offset_hours = now.hour + (now.minute / 60.0)
                    
                    for device in devices:
                        payload = generate_telemetry_point(device.device_type, time_offset_hours)
                        metric = DeviceMetric(
                            device_id=device.id,
                            cpu_usage=payload["cpu_usage"],
                            memory_usage=payload["memory_usage"],
                            latency=payload["latency"],
                            packet_loss=payload["packet_loss"],
                            bandwidth_usage=payload["bandwidth_usage"],
                            anomaly_score=0.0,
                            anomaly_detected=False,
                            timestamp=now
                        )
                        session.add(metric)
                        print(f"[SIMULATOR] Telemetry pushed: {device.device_name} -> CPU: {payload['cpu_usage']}%, Latency: {payload['latency']}ms")
                    
                    await session.commit()
            
        except Exception as e:
            print(f"[SIMULATOR] Error occurred in simulation loop: {e}", file=sys.stderr)
            
        await asyncio.sleep(interval_seconds)

async def main():
    parser = argparse.ArgumentParser(description="AETHER NOC Telemetry Simulator Daemon")
    parser.add_argument("--seed", action="store_true", help="Instantly seed database with historical metrics")
    parser.add_argument("--hours", type=int, default=24, help="Amount of hours to seed (default: 24)")
    parser.add_argument("--live", action="store_true", help="Start the continuous live telemetry simulation loop")
    parser.add_argument("--interval", type=int, default=5, help="Simulation loop check interval in seconds (default: 5)")
    args = parser.parse_args()

    # Ensure at least one argument is provided
    if not args.seed and not args.live:
        parser.print_help()
        sys.exit(0)

    # Inquire about registered devices in DB
    async with async_session() as session:
        result = await session.execute(select(Device))
        devices = result.scalars().all()
        
    if not devices:
        print("[ERROR] No devices found in inventory database.")
        print("Please register devices via the UI or REST API before running this simulator.")
        sys.exit(1)

    if args.seed:
        async with async_session() as session:
            await seed_historical_metrics(session, devices, hours=args.hours)

    if args.live:
        await run_live_simulation(interval_seconds=args.interval)

if __name__ == "__main__":
    # Standard asyncio harness loop execution
    asyncio.run(main())
