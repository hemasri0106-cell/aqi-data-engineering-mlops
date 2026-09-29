import requests
import json
from datetime import datetime
import time

def monitor_service(api_url: str = "http://localhost:8000", output_path: str = "reports/monitoring/service_metrics.json"):
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_available": False,
        "regression_model_loaded": False,
        "classification_model_loaded": False,
        "latency_ms": None,
        "status": "FAIL"
    }
    
    start_time = time.time()
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        latency = (time.time() - start_time) * 1000
        
        report["latency_ms"] = float(f"{latency:.2f}")
        report["api_available"] = True
        
        if response.status_code == 200:
            data = response.json()
            report["regression_model_loaded"] = data.get("regression_model_loaded", False)
            report["classification_model_loaded"] = data.get("classification_model_loaded", False)
            report["status"] = "PASS" if (report["regression_model_loaded"] and report["classification_model_loaded"]) else "DEGRADED"
        else:
            report["error_code"] = response.status_code
            
    except Exception as e:
        report["error"] = str(e)
        
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
        
    return report

if __name__ == "__main__":
    print(monitor_service())
