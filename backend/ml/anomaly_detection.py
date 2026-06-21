"""
ml/anomaly_detection.py
======================
Machine Learning Anomaly Detection Service

WHY THIS FILE EXISTS:
    This module encapsulates the Isolation Forest pipeline used to flag abnormal 
    network metrics (e.g. spikes in CPU usage, memory usage, latency, packet loss).
    It is loaded in the ingestion pipeline to analyze data in real time.
"""

import os
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_detector.joblib")

class AnomalyDetector:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        """
        Loads the persisted Isolation Forest binary from saved_models/.
        """
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print("[ML] Loaded anomaly_detector.joblib successfully.")
            except Exception as e:
                print(f"[ML] Error loading anomaly_detector.joblib: {e}")
                self.model = None

    def train(self, data: pd.DataFrame):
        """
        Trains the Isolation Forest model on historical telemetry data.
        
        Args:
            data (pd.DataFrame): Training metrics containing cpu_usage, memory_usage, latency, packet_loss, bandwidth_usage.
        """
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        features = ["cpu_usage", "memory_usage", "latency", "packet_loss", "bandwidth_usage"]
        training_subset = data[features]
        
        # Isolation Forest contamination represents estimated ratio of anomalies
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )
        
        self.model.fit(training_subset)
        joblib.dump(self.model, MODEL_PATH)
        print("[ML] Isolation Forest model trained and saved successfully.")

    def predict(self, metrics_vector: list) -> dict:
        """
        Predicts whether a metrics data point is anomalous.
        
        Args:
            metrics_vector (list): [cpu_usage, memory_usage, latency, packet_loss, bandwidth_usage]
            
        Returns:
            dict: {
                "anomaly_score": float,  # Normalized between 0.0 and 1.0 (larger is more anomalous)
                "anomaly_detected": bool
            }
        """
        if not self.model:
            # Fallback heuristics if model is not trained yet
            cpu_usage, memory_usage, latency, packet_loss, bandwidth_usage = metrics_vector
            is_anomaly = bool(
                cpu_usage > 90.0 or 
                memory_usage > 90.0 or 
                latency > 250.0 or 
                packet_loss > 5.0
            )
            return {
                "anomaly_score": 0.85 if is_anomaly else 0.12,
                "anomaly_detected": is_anomaly
            }
            
        try:
            # Format input array as single-row DataFrame
            columns = ["cpu_usage", "memory_usage", "latency", "packet_loss", "bandwidth_usage"]
            df = pd.DataFrame([metrics_vector], columns=columns)
            
            # Predict returns 1 (normal) and -1 (anomaly)
            pred = self.model.predict(df)[0]
            
            # score_samples returns negative anomaly score. Values close to -1 are anomalous.
            raw_score = float(self.model.score_samples(df)[0])
            # Map score to [0.0, 1.0] range (raw_score is typically between -1.0 and 0.0)
            normalized_score = float(max(0.0, min(1.0, -raw_score)))
            
            return {
                "anomaly_score": normalized_score,
                "anomaly_detected": bool(pred == -1)
            }
        except Exception as e:
            print(f"[ML] Error in Isolation Forest prediction: {e}")
            return {
                "anomaly_score": 0.0,
                "anomaly_detected": False
            }

