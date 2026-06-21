"""
ml/predict.py
=============
ML Inference Wrapper

WHY THIS FILE EXISTS:
    This script acts as the interface between the FastAPI web application and the
    trained machine learning models. It loads the persisted model files from saved_models/
    and provides unified prediction helper functions.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.metric import DeviceMetric
from ml.anomaly_detection import AnomalyDetector
from ml.failure_prediction import FailurePredictor

# Initialize singletons
anomaly_detector = AnomalyDetector()
failure_predictor = FailurePredictor()

def detect_anomaly(cpu_usage: float, memory_usage: float, latency: float, packet_loss: float, bandwidth_usage: float) -> dict:
    """
    Feeds current telemetry metrics to the Isolation Forest model.
    """
    vector = [cpu_usage, memory_usage, latency, packet_loss, bandwidth_usage]
    return anomaly_detector.predict(vector)

async def predict_failure(db: AsyncSession, device_id: str) -> dict:
    """
    Retrieves the latest telemetry metrics for a device, and maps them
    to the Random Forest classifier to compute failure risk.
    """
    stmt = (
        select(DeviceMetric)
        .filter(DeviceMetric.device_id == device_id)
        .order_by(DeviceMetric.timestamp.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    latest_metric = result.scalars().first()
    
    if not latest_metric:
        # Fallback if no metric data exists
        return {
            "probability": 0.0,
            "risk_level": "low",
            "metrics_analyzed": 0
        }
        
    vector = [
        latest_metric.cpu_usage,
        latest_metric.memory_usage,
        latest_metric.latency,
        latest_metric.packet_loss,
        latest_metric.bandwidth_usage
    ]
    
    pred_res = failure_predictor.predict_probability(vector)
    pred_res["metrics_analyzed"] = 1
    return pred_res

async def forecast_capacity(db: AsyncSession, device_id: str, hours_ahead: int = 24) -> List[Dict]:
    """
    Calculates capacity forecasts for CPU and bandwidth over the next hours
    using a linear regression slope computed from historical telemetry.
    """
    # Fetch past 24 hours of telemetry metrics to build trend lines
    yesterday = datetime.utcnow() - timedelta(days=1)
    stmt = (
        select(DeviceMetric)
        .filter(DeviceMetric.device_id == device_id)
        .filter(DeviceMetric.timestamp >= yesterday)
        .order_by(DeviceMetric.timestamp.asc())
    )
    result = await db.execute(stmt)
    history = result.scalars().all()
    
    # Defaults if history is insufficient
    avg_cpu = 30.0
    avg_band = 50.0
    cpu_slope = 0.0
    band_slope = 0.0
    
    if len(history) > 1:
        # Extract features and timestamps as relative index
        cpus = [h.cpu_usage for h in history]
        bands = [h.bandwidth_usage for h in history]
        times = [(h.timestamp - history[0].timestamp).total_seconds() / 3600.0 for h in history]
        
        # Fit linear regression using numpy
        try:
            cpu_fit = np.polyfit(times, cpus, 1)
            cpu_slope = float(cpu_fit[0])
            avg_cpu = float(cpus[-1])
            
            band_fit = np.polyfit(times, cpus, 1) # Note: can fit on bandwidth
            band_slope = float(np.polyfit(times, bands, 1)[0])
            avg_band = float(bands[-1])
        except Exception:
            pass
            
    # Project into future hourly points
    forecast_points = []
    base_time = datetime.utcnow()
    
    for i in range(1, hours_ahead + 1):
        target_time = base_time + timedelta(hours=i)
        
        # Extrapolate CPU & Bandwidth, clamping to boundaries
        predicted_cpu = max(0.0, min(100.0, avg_cpu + cpu_slope * i))
        predicted_band = max(0.0, avg_band + band_slope * i)
        
        forecast_points.append({
            "timestamp": target_time,
            "cpu_usage_predicted": round(predicted_cpu, 2),
            "bandwidth_usage_predicted": round(predicted_band, 2)
        })
        
    return forecast_points

