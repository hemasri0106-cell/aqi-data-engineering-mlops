import pandas as pd
import json
from datetime import datetime

def check_data_quality(df: pd.DataFrame, output_path: str = "reports/monitoring/data_quality_report.json"):
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_rows": len(df),
        "features": {},
        "overall_status": "PASS"
    }

    if df.empty:
        report["overall_status"] = "FAIL"
        report["error"] = "DataFrame is empty."
        with open(output_path, "w") as f:
            json.dump(report, f, indent=4)
        return report

    # 1. Missing values
    missing_pct = (df.isnull().sum() / len(df)) * 100
    for col, pct in missing_pct.items():
        status = "PASS"
        if pct > 10.0:  # threshold: 10%
            status = "WARNING"
        if pct > 30.0:  # threshold: 30%
            status = "FAIL"
            
        report["features"].setdefault(col, {})["missing_pct"] = pct
        report["features"][col]["missing_status"] = status
        
        if status == "FAIL":
            report["overall_status"] = "FAIL"

    # 2. Invalid numeric values (negatives)
    for col in ["pm25", "no2", "aqi"]:
        if col in df.columns:
            negative_count = (df[col] < 0).sum()
            status = "PASS"
            if negative_count > 0:
                status = "FAIL"
                report["overall_status"] = "FAIL"
            report["features"][col]["negative_count"] = int(negative_count)
            report["features"][col]["negative_status"] = status

    # 3. Duplicate records
    if "station_id" in df.columns and "date" in df.columns:
        duplicates = df.duplicated(subset=["station_id", "date"]).sum()
        status = "PASS"
        if duplicates > 0:
            status = "FAIL"
            report["overall_status"] = "FAIL"
        report["duplicate_station_dates"] = int(duplicates)
        report["duplicate_status"] = status

    # 4. Valid AQI Categories
    if "aqi_category" in df.columns:
        valid_cats = {"Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"}
        invalid_cats = set(df["aqi_category"].dropna().unique()) - valid_cats
        status = "PASS"
        if invalid_cats:
            status = "FAIL"
            report["overall_status"] = "FAIL"
        report["features"]["aqi_category"]["invalid_categories"] = list(invalid_cats)
        report["features"]["aqi_category"]["category_status"] = status

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
        
    return report

if __name__ == "__main__":
    df = pd.read_csv("data/ml/features/ml_features_full.csv")
    print(check_data_quality(df))
