import pandas as pd
import json
from datetime import datetime
from scipy.stats import ks_2samp

def check_feature_drift(ref_df: pd.DataFrame, curr_df: pd.DataFrame, output_path: str = "reports/monitoring/drift_report.json"):
    features_to_monitor = [
        "pm25", "no2", "aqi", "temperature_c", 
        "humidity_pct", "precipitation_mm", "wind_speed_kmh"
    ]
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "method": "Kolmogorov-Smirnov Test",
        "threshold_p_value": 0.05,
        "features": {},
        "overall_status": "PASS"
    }
    
    # If the current dataset is too small, drift cannot be reliably calculated
    if len(curr_df) < 30:
        report["overall_status"] = "WARNING"
        report["warning"] = f"Current dataset size ({len(curr_df)}) is too small for statistical drift detection."
        with open(output_path, "w") as f:
            json.dump(report, f, indent=4)
        return report

    for feature in features_to_monitor:
        if feature in ref_df.columns and feature in curr_df.columns:
            # Drop NaNs for KS test
            ref_data = ref_df[feature].dropna()
            curr_data = curr_df[feature].dropna()
            
            if len(ref_data) > 0 and len(curr_data) > 0:
                stat, p_value = ks_2samp(ref_data, curr_data)
                
                status = "PASS"
                if p_value < report["threshold_p_value"]:
                    status = "DRIFT_DETECTED"
                    report["overall_status"] = "WARNING"  # Drift is a warning to trigger retraining, not a hard fail
                
                report["features"][feature] = {
                    "ks_statistic": float(stat),
                    "p_value": float(p_value),
                    "status": status
                }
            else:
                report["features"][feature] = {
                    "status": "NOT_ENOUGH_DATA"
                }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

    return report

if __name__ == "__main__":
    ref_df = pd.read_csv("data/ml/train/train.csv")
    # For demonstration, use recent 30 rows as "current"
    curr_df = pd.read_csv("data/ml/features/ml_features_full.csv").tail(30)
    print(check_feature_drift(ref_df, curr_df))
