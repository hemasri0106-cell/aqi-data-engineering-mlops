import pandas as pd
import json
from datetime import datetime
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score, accuracy_score, precision_score, recall_score, f1_score

def check_model_performance(predictions: list, actuals: list, task_type: str = "regression", output_path: str = "reports/monitoring/model_performance_report.json"):
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "task_type": task_type,
        "sample_size": len(predictions),
        "metrics": {},
        "status": "PASS"
    }
    
    if len(predictions) == 0 or len(actuals) == 0 or len(predictions) != len(actuals):
        report["status"] = "FAIL"
        report["error"] = "Invalid predictions or actuals length."
        with open(output_path, "w") as f:
            json.dump(report, f, indent=4)
        return report

    if task_type == "regression":
        mae = mean_absolute_error(actuals, predictions)
        rmse = root_mean_squared_error(actuals, predictions)
        r2 = r2_score(actuals, predictions)
        
        report["metrics"] = {
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2)
        }
        
        # Simple threshold check
        if mae > 50.0 or r2 < 0.0:
            report["status"] = "WARNING"
            
    elif task_type == "classification":
        acc = accuracy_score(actuals, predictions)
        prec = precision_score(actuals, predictions, average="macro", zero_division=0)
        rec = recall_score(actuals, predictions, average="macro", zero_division=0)
        f1 = f1_score(actuals, predictions, average="macro", zero_division=0)
        
        report["metrics"] = {
            "accuracy": float(acc),
            "macro_precision": float(prec),
            "macro_recall": float(rec),
            "macro_f1": float(f1)
        }
        
        # Simple threshold check
        if acc < 0.5:
            report["status"] = "WARNING"

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
        
    return report

if __name__ == "__main__":
    # Test execution
    check_model_performance([100, 110, 120], [105, 115, 110], "regression")
    check_model_performance(["Good", "Poor"], ["Good", "Moderate"], "classification", "reports/monitoring/model_performance_clf.json")
