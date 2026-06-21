"""
ml/failure_prediction.py
========================
Machine Learning Device Failure Prediction Service

WHY THIS FILE EXISTS:
    This module encapsulates the Random Forest Classifier pipeline. It calculates
    the likelihood that a device will fail in the near future based on rolling 
    averages and trends of its performance telemetry.
"""

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(MODEL_DIR, "failure_predictor.joblib")

class FailurePredictor:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        """
        Loads the persisted Random Forest model from saved_models/.
        """
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print("[ML] Loaded failure_predictor.joblib successfully.")
            except Exception as e:
                print(f"[ML] Error loading failure_predictor.joblib: {e}")
                self.model = None

    def train(self, features: pd.DataFrame, labels: pd.Series):
        """
        Trains the Random Forest Classifier on engineered telemetry features.
        
        Args:
            features (pd.DataFrame): Training features table.
            labels (pd.Series): Target labels (0 = healthy, 1 = failure risk).
        """
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42
        )
        self.model.fit(features, labels)
        joblib.dump(self.model, MODEL_PATH)
        print("[ML] Random Forest failure classifier trained and saved.")

    def predict_probability(self, features_vector: list) -> dict:
        """
        Predicts the device failure probability.
        
        Args:
            features_vector (list): [cpu_usage, memory_usage, latency, packet_loss, bandwidth_usage]
            
        Returns:
            dict: {
                "probability": float,  # Value between 0.0 and 1.0
                "risk_level": str      # "low", "medium", "critical"
            }
        """
        if not self.model:
            # Fallback heuristic calculation if model not trained
            cpu, mem, lat, pkt, band = features_vector
            # Formulate failure risk score (weighted telemetry stress)
            stress_score = (
                (cpu / 100.0) * 0.35 + 
                (mem / 100.0) * 0.25 + 
                (min(lat, 500) / 500.0) * 0.20 + 
                (min(pkt, 15) / 15.0) * 0.20
            )
            prob = float(max(0.0, min(0.99, stress_score)))
            
            if prob >= 0.70:
                risk = "critical"
            elif prob >= 0.30:
                risk = "medium"
            else:
                risk = "low"
                
            return {
                "probability": prob,
                "risk_level": risk
            }
            
        try:
            columns = ["cpu_usage", "memory_usage", "latency", "packet_loss", "bandwidth_usage"]
            df = pd.DataFrame([features_vector], columns=columns)
            
            # predict_proba returns array of shape [n_samples, n_classes]
            prob = float(self.model.predict_proba(df)[0][1])
            
            if prob >= 0.70:
                risk = "critical"
            elif prob >= 0.30:
                risk = "medium"
            else:
                risk = "low"
                
            return {
                "probability": prob,
                "risk_level": risk
            }
        except Exception as e:
            print(f"[ML] Error in RandomForest failure prediction: {e}")
            return {
                "probability": 0.0,
                "risk_level": "low"
            }

