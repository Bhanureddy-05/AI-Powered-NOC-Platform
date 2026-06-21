"""
app/schemas/ml.py
=================
Pydantic Schemas for ML Predictions, Health Scores, and Forecasts

WHY THIS FILE EXISTS:
    Specifies output shapes for real-time predictions, predictive maintenance risks,
    historical anomaly aggregates, capacity trends, and retraining actions.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class DevicePredictionSummary(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    health_score: float
    failure_probability: float
    risk_level: str
    anomaly_detected: bool
    last_metric_timestamp: Optional[datetime] = None

class CapacityForecastPoint(BaseModel):
    timestamp: datetime
    cpu_usage_predicted: float
    bandwidth_usage_predicted: float

class DevicePredictionDetails(BaseModel):
    device_id: str
    device_name: str
    health_score: float
    failure_probability: float
    risk_level: str
    anomalies_count_24h: int
    recent_anomaly_scores: List[float]
    forecast: List[CapacityForecastPoint]
    maintenance_status: str # "good", "warning", "critical"

class MLRetrainResponse(BaseModel):
    status: str
    message: str
    retrained_at: datetime
    metrics_trained: int
