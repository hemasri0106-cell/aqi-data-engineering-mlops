import pandas as pd
import json
from src.monitoring.data_quality import check_data_quality
from src.monitoring.drift_monitor import check_feature_drift

def run_all_monitoring():
    print("Running Monitoring Pipeline...")
    
    try:
        # Load datasets
        print("Loading datasets...")
        curr_df = pd.read_csv("data/ml/features/ml_features_full.csv")
        ref_df = pd.read_csv("data/ml/train/train.csv")
        
        # 1. Data Quality
        print("Checking Data Quality...")
        dq_report = check_data_quality(curr_df)
        print(f"Data Quality Status: {dq_report['overall_status']}")
        
        # 2. Feature Drift
        print("Checking Feature Drift...")
        # We compare the training reference to the most recent 30 days of data
        # In a real system, curr_df would be strictly the new unseen data since last training.
        recent_curr = curr_df.sort_values(by="date").tail(30)
        drift_report = check_feature_drift(ref_df, recent_curr)
        print(f"Drift Status: {drift_report['overall_status']}")
        
        # 3. Retraining Evaluation
        retrain = False
        if dq_report['overall_status'] == "FAIL":
            print("RETRAINING BLOCKED: Data quality failed. Fix data before retraining.")
        elif drift_report['overall_status'] == "WARNING":
            print("RETRAINING SUGGESTED: Feature drift detected.")
            retrain = True
        else:
            print("RETRAINING NOT NEEDED: System is healthy.")
            
        with open("reports/monitoring/retraining_status.json", "w") as f:
            json.dump({
                "timestamp": dq_report["timestamp"],
                "data_quality_status": dq_report["overall_status"],
                "drift_status": drift_report["overall_status"],
                "retrain_suggested": retrain
            }, f, indent=4)
            
        print("Monitoring completed successfully. Reports saved in reports/monitoring/")
        
    except Exception as e:
        print(f"Monitoring pipeline failed: {e}")

if __name__ == "__main__":
    run_all_monitoring()
