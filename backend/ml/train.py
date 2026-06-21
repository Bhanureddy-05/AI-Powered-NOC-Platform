"""
ml/train.py
===========
Model Training Pipeline Script

WHY THIS FILE EXISTS:
    This script is executed (manually or periodically via cron) to load historical
    telemetry data from the PostgreSQL database, train the machine learning models
    (Isolation Forest and Random Forest), and save them to saved_models/ using joblib.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.metric import DeviceMetric
from ml.anomaly_detection import AnomalyDetector, MODEL_PATH as AD_PATH
from ml.failure_prediction import FailurePredictor, MODEL_PATH as FP_PATH

async def train_models_from_db(db: AsyncSession) -> int:
    """
    Main orchestrator to fetch telemetry and retrain machine learning models.
    Returns:
        int: Number of metric records trained on.
    """
    print("[ML] Starting model retraining from database...")
    
    # 1. Fetch metrics
    stmt = select(DeviceMetric).order_by(DeviceMetric.timestamp.desc()).limit(5000)
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    
    # 2. Build pandas DataFrame
    data_list = []
    for m in metrics:
        data_list.append({
            "cpu_usage": m.cpu_usage,
            "memory_usage": m.memory_usage,
            "latency": m.latency,
            "packet_loss": m.packet_loss,
            "bandwidth_usage": m.bandwidth_usage
        })
        
    df_db = pd.DataFrame(data_list)
    
    # 3. Bootstrap with synthetic data if history is small (< 50 rows)
    if len(df_db) < 50:
        print(f"[ML] Database contains only {len(df_db)} metric records. Generating synthetic training dataset...")
        
        # Normal operations baseline
        np.random.seed(42)
        n_samples = 150
        synthetic_normal = pd.DataFrame({
            "cpu_usage": np.random.normal(35.0, 10.0, n_samples),
            "memory_usage": np.random.normal(45.0, 12.0, n_samples),
            "latency": np.random.normal(20.0, 5.0, n_samples),
            "packet_loss": np.random.normal(0.02, 0.05, n_samples),
            "bandwidth_usage": np.random.normal(55.0, 15.0, n_samples)
        })
        
        # Anomalies/Failures baseline
        n_anoms = 15
        synthetic_anomalies = pd.DataFrame({
            "cpu_usage": np.random.normal(92.0, 3.0, n_anoms),
            "memory_usage": np.random.normal(94.0, 2.0, n_anoms),
            "latency": np.random.normal(320.0, 40.0, n_anoms),
            "packet_loss": np.random.normal(8.5, 2.0, n_anoms),
            "bandwidth_usage": np.random.normal(12.0, 5.0, n_anoms)
        })
        
        df_synthetic = pd.concat([synthetic_normal, synthetic_anomalies], ignore_index=True)
        # Clip percentages
        df_synthetic["cpu_usage"] = df_synthetic["cpu_usage"].clip(0, 100)
        df_synthetic["memory_usage"] = df_synthetic["memory_usage"].clip(0, 100)
        df_synthetic["packet_loss"] = df_synthetic["packet_loss"].clip(0, 100)
        
        if not df_db.empty:
            df = pd.concat([df_db, df_synthetic], ignore_index=True)
        else:
            df = df_synthetic
    else:
        df = df_db
        
    # 4. Train Anomaly Detection (Isolation Forest)
    detector = AnomalyDetector()
    detector.train(df)
    
    # 5. Label data for Failure Classifier (Random Forest)
    # Target label is 1 (failure) if multiple telemetry parameters indicate extreme load
    labels = []
    features = ["cpu_usage", "memory_usage", "latency", "packet_loss", "bandwidth_usage"]
    
    for idx, row in df.iterrows():
        # Label 1 if CPU > 85% AND Memory > 85%, or Latency > 200ms AND Packet Loss > 3%
        cpu_mem_fail = row["cpu_usage"] > 85.0 and row["memory_usage"] > 85.0
        network_fail = row["latency"] > 200.0 and row["packet_loss"] > 3.0
        extreme_stress = row["cpu_usage"] > 95.0 or row["packet_loss"] > 8.0
        
        if cpu_mem_fail or network_fail or extreme_stress:
            labels.append(1)
        else:
            labels.append(0)
            
    labels_series = pd.Series(labels)
    
    # Train Failure Classifier
    predictor = FailurePredictor()
    predictor.train(df[features], labels_series)
    
    print(f"[ML] Retraining complete. Models saved to saved_models/. Trained on {len(df)} samples.")
    return len(df)

if __name__ == "__main__":
    # If run directly as a script, we alert that it requires DB connection context
    print("Please trigger model retraining via the API endpoint POST /api/v1/ml/retrain or startup lifecycle events.")

