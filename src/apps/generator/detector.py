import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from collections import deque


class WaterLeakDetector:
    """
    Combines Isolation Forest (hourly usage vectors) and a zero-hour heuristic
    (at least one hour of zero water consumption per 24 hours) for detecting water leaks per household.
    """
    def __init__(self, contamination=0.01, random_state=42):
        self.contamination = contamination
        self.random_state = random_state
        self.models = {}          # household_id -> fitted IsolationForest
        self.buffers = {}         # household_id -> deque of recent hourly volumes

    def train(self, historic_df: pd.DataFrame):
        """
        Trains an Isolation Forest model per household using 24-hour sliding usage vectors.
        :param historic_df: Historical consumption DataFrame (must contain 'timestamp', 'volume_liter', 'household_id')
        """
        for household_id, group in historic_df.groupby('household_id'):
            group = group.sort_values('timestamp')
            volumes = group['volume_liter'].values

            # Construct 24-hour sliding window vectors
            if len(volumes) < 24:
                print(f"Skipping {household_id}: Insufficient data for 24-hour window.")
                continue

            # Shape: (N - 23, 24) where each row is 24 consecutive hourly readings
            window_matrix = np.lib.stride_tricks.sliding_window_view(volumes, window_shape=24)

            # Fit Isolation Forest on 24h consumption profiles
            iso_forest = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100
            )
            iso_forest.fit(window_matrix)
            self.models[household_id] = iso_forest

            # Initialize buffer with the last 24 hours of training data for real-time tracking
            # The buffer size is restricted to the last 24 hours, when a new value gets added
            # and it is at full capacity, then the first value gets popped.
            # The order is sequential just like the time.
            self.buffers[household_id] = deque(volumes[-24:], maxlen=24)


    def predict_hourly(self, single_row_df: pd.DataFrame, use_isolation_forest: bool = True) -> pd.DataFrame:
        """
        Processes a single incoming streaming hour for a household, adds it to the 24 hour buffer.
        Then uses the 24 hours buffer of the last 24 hours to make a prediction for this hour.
        :param single_row_df: Single-row DataFrame containing 'household_id', 'volume_liter', and 'timestamp'
        :param use_isolation_forest: If True (default), use isolation forest with the mandatory zero-gap check.
        :return: DataFrame containing all data after prediction necessary for a new row in the database.
        """
        household_id = single_row_df["household_id"].iloc[0]
        volume = single_row_df["volume_liter"].iloc[0]
        timestamp = single_row_df["timestamp"].iloc[0]

        if household_id not in self.models:
            raise ValueError(f"No trained model found for household: {household_id}")

        # Update sliding buffer
        buffer = self.buffers[household_id]
        buffer.append(volume)

        # Keep only the most recent 24 hourly readings
        # Although we use a deque with maxlength=24, we still add this as an extra safety guard if we want to switch to a list later
        if len(buffer) > 24:
            buffer = buffer[-24:]
        self.buffers[household_id] = buffer

        # Warm-up check
        if len(buffer) < 24:
            return pd.DataFrame([{
                "timestamp": timestamp,
                "household_id": household_id,
                "volume_liter": volume,
                "predicted": False,
                "is_leak": False,
                "zero_gap_anomaly": False,
                "isolation_forest_anomaly": False
            }])

        window_vector = np.array(buffer).reshape(1, -1)

        # Zero-gap rule: slow continuous drip leak if NO hour in 24h had 0 water usage
        zero_gap_anomaly = not (0 in buffer)

        # Isolation Forest (IF) anomaly detection (e.g. burst pipe or abnormal 3AM spikes)
        # sklearn outputs -1 for anomaly, 1 for normal
        if use_isolation_forest:
            if_pred = self.models[household_id].predict(window_vector)[0]
            if_score = float(self.models[household_id].score_samples(window_vector)[0])
            if_anomaly = (if_pred == -1)
        else:
            if_anomaly = False
            if_score = 0.0

        # If there is some sort of anomaly, it is a leak
        is_leak = zero_gap_anomaly or if_anomaly

        return pd.DataFrame([{
            "timestamp": timestamp,
            "household_id": household_id,
            "volume_liter": volume,
            "predicted": True,
            "is_leak": is_leak,
            "zero_gap_anomaly": zero_gap_anomaly,
            "isolation_forest_anomaly": if_anomaly
        }])


    def save(self, model_directory: str, household_id: str) -> str:
        """
        Saves the Isolation Forest model and current 24h buffer for a specific household.

        :param model_directory: Directory path where the model file should be stored.
        :param household_id: ID of the household to save.
        :return: Path to the saved model file.
        """
        if household_id not in self.models:
            raise ValueError(f"No trained model found to save for household: {household_id}")

        os.makedirs(model_directory, exist_ok=True)
        file_path = os.path.join(model_directory, f"{household_id}.joblib")

        # Package the fitted estimator and current buffer state
        payload = {
            "model": self.models[household_id],
            "buffer": self.buffers.get(household_id, deque(maxlen=24)),
            "contamination": self.contamination,
            "random_state": self.random_state
        }
        joblib.dump(payload, file_path)

        return file_path


    def load(self, model_directory: str, household_id: str) -> None:
        """
        Loads a saved Isolation Forest model and buffer state for a specific household.

        :param model_directory: Directory path where the model file is stored.
        :param household_id: ID of the household to load.
        """
        file_path = os.path.join(model_directory, f"{household_id}.joblib")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No saved model found at: {file_path}")

        payload = joblib.load(file_path)

        self.models[household_id] = payload["model"]
        self.buffers[household_id] = payload["buffer"]
