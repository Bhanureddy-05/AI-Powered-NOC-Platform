"""
app/api/v1/routes/ml.py
=======================
Machine Learning Analytics API Router

WHY THIS FILE EXISTS:
    Exposes endpoints for fetching real-time device health indices, failure probabilities,
    capacity forecasting arrays, and triggering model retraining.
"""

from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.session import get_db
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.user import User
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.ml import DevicePredictionSummary, DevicePredictionDetails, MLRetrainResponse
from ml.predict import predict_failure, forecast_capacity
from ml.train import train_models_from_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/ml", tags=["AI/ML Analytics"])

@router.get("/predictions", response_model=List[DevicePredictionSummary])
async def get_all_device_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns health scores, failure probabilities, and status indicators for all monitored devices.
    """
    # 1. Fetch all devices
    stmt = select(Device)
    result = await db.execute(stmt)
    devices = result.scalars().all()
    
    predictions = []
    
    for device in devices:
        # Run failure probability prediction
        pred = await predict_failure(db, device.id)
        
        # Health score = (1 - failure_probability) * 100
        prob = pred["probability"]
        health_score = round((1.0 - prob) * 100.0, 1)
        
        # Check if the latest metric record is marked as an anomaly
        m_stmt = (
            select(DeviceMetric)
            .filter(DeviceMetric.device_id == device.id)
            .order_by(DeviceMetric.timestamp.desc())
            .limit(1)
        )
        m_res = await db.execute(m_stmt)
        latest_metric = m_res.scalars().first()
        
        anomaly_detected = latest_metric.anomaly_detected if latest_metric else False
        last_ts = latest_metric.timestamp if latest_metric else None
        
        predictions.append({
            "device_id": device.id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "health_score": health_score,
            "failure_probability": round(prob, 3),
            "risk_level": pred["risk_level"],
            "anomaly_detected": anomaly_detected,
            "last_metric_timestamp": last_ts
        })
        
    # Sort by lowest health score first (highest risk first)
    predictions.sort(key=lambda x: x["health_score"])
    return predictions

@router.get("/predictions/{device_id}", response_model=DevicePredictionDetails)
async def get_device_prediction_details(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns detailed ML diagnostics (recent anomaly counts, predictions, capacity trend forecasts) for a single device.
    """
    # 1. Verify device exists
    dev_stmt = select(Device).filter(Device.id == device_id)
    dev_res = await db.execute(dev_stmt)
    device = dev_res.scalars().first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found."
        )
        
    # 2. Run failure predictor
    pred = await predict_failure(db, device.id)
    prob = pred["probability"]
    health_score = round((1.0 - prob) * 100.0, 1)
    
    # 3. Count anomalies in the last 24h
    yesterday = datetime.utcnow() - timedelta(days=1)
    anom_stmt = (
        select(func.count(DeviceMetric.id))
        .filter(DeviceMetric.device_id == device_id)
        .filter(DeviceMetric.timestamp >= yesterday)
        .filter(DeviceMetric.anomaly_detected == True)
    )
    anom_res = await db.execute(anom_stmt)
    anom_count = anom_res.scalar() or 0
    
    # 4. Fetch recent anomaly scores
    scores_stmt = (
        select(DeviceMetric.anomaly_score)
        .filter(DeviceMetric.device_id == device_id)
        .order_by(DeviceMetric.timestamp.desc())
        .limit(10)
    )
    scores_res = await db.execute(scores_stmt)
    recent_scores = [float(s) for s in scores_res.scalars().all()]
    
    # 5. Capacity forecasts
    forecasts = await forecast_capacity(db, device_id, hours_ahead=24)
    
    maintenance_status = "good"
    if health_score < 50.0:
        maintenance_status = "critical"
    elif health_score < 80.0:
        maintenance_status = "warning"
        
    return {
        "device_id": device.id,
        "device_name": device.device_name,
        "health_score": health_score,
        "failure_probability": round(prob, 3),
        "risk_level": pred["risk_level"],
        "anomalies_count_24h": anom_count,
        "recent_anomaly_scores": recent_scores,
        "forecast": forecasts,
        "maintenance_status": maintenance_status
    }

@router.post("/retrain", response_model=MLRetrainResponse)
async def trigger_model_retraining(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Retrains the Isolation Forest (anomaly) and Random Forest (failure) classifiers.
    Requires Admin or Operator credentials.
    """
    try:
        samples_trained = await train_models_from_db(db)
        
        # Generate audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="ml_retrained",
            details=f"ML Models retrained successfully. Samples: {samples_trained}",
            ip_address=None
        )
        db.add(audit)
        
        return {
            "status": "success",
            "message": "Retraining finished successfully.",
            "retrained_at": datetime.utcnow(),
            "metrics_trained": samples_trained
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining failed: {e}"
        )
