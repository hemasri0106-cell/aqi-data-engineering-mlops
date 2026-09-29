# AQI Prediction - Deployment Guide

This document describes how to build and deploy the AQI Prediction API using Docker and MLflow.

## Prerequisites
- Docker & Docker Desktop installed and running
- Python 3.12+ (if running MLflow server locally)
- PostgreSQL database for MLflow tracking backend

## Overview
The architecture consists of three core components:
1. **PostgreSQL Database (`mlflow_db`)**: Stores MLflow run tracking and model registry metadata.
2. **Local MLflow Server**: Runs on the host machine to serve model metadata and point to local artifacts.
3. **FastAPI Docker Container**: The API runtime, built with Python 3.12-slim. It reads models directly from the local artifact store by bind-mounting the host's directory.

## Step 1: Start MLflow Server
The container needs access to the MLflow tracking API. Start the MLflow server on your host machine:

```bash
# From the project root with the active virtual environment
mlflow server \
  --backend-store-uri postgresql://postgres:<YOUR_PASSWORD>@localhost:5432/mlflow_db \
  --default-artifact-root "file:///$PWD/mlflow_artifacts" \
  --host 0.0.0.0 \
  --port 5000 \
  --disable-security-middleware
```

## Step 2: Build the API Container
Build the FastAPI application as a Docker image:

```bash
docker build -t aqi-prediction-api .
```

## Step 3: Run the API Container
To allow the container to access your host's MLflow server and local artifacts, you must bind-mount the artifact directory and use `--add-host` or `host.docker.internal`.

### Windows Command (PowerShell):
```powershell
docker run -d `
  -p 8000:8000 `
  -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" `
  -e MODEL_VERSION=1 `
  --mount type=bind,source="C:\Users\hemas\OneDrive\Desktop\mlops project\AQI-Prediction-Project\mlflow_artifacts",target="/C:/Users/hemas/OneDrive/Desktop/mlops project/AQI-Prediction-Project/mlflow_artifacts" `
  --name aqi_api `
  aqi-prediction-api
```

### Linux/macOS Command:
```bash
docker run -d \
  -p 8000:8000 \
  -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" \
  -e MODEL_VERSION=1 \
  -v $(pwd)/mlflow_artifacts:$(pwd)/mlflow_artifacts \
  --name aqi_api \
  aqi-prediction-api
```

## Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Regression (Predict Next-Day AQI)
```bash
curl -X POST "http://localhost:8000/predict/regression" \
     -H "Content-Type: application/json" \
     -d '{
           "station_id": 1,
           "city": "Delhi",
           "pm25": 45.2,
           "no2": 15.1,
           "aqi": 120.0,
           "aqi_category": "Moderate",
           "day_of_week": 3,
           "month": 9
         }'
```

### 3. Classification (Predict Next-Day AQI Category)
```bash
curl -X POST "http://localhost:8000/predict/classification" \
     -H "Content-Type: application/json" \
     -d '{
           "station_id": 1,
           "city": "Delhi",
           "pm25": 45.2,
           "no2": 15.1,
           "aqi": 120.0,
           "aqi_category": "Moderate",
           "day_of_week": 3,
           "month": 9
         }'
```

## Troubleshooting
- **`MlflowException: No such artifact: ''`**: The container cannot find the artifact files. Ensure the host's `mlflow_artifacts` path is correctly bind-mounted to the EXACT same path structure inside the container.
- **Model Incompatibility**: If you see an unpickling error (`ModuleNotFoundError: No module named 'numpy._core.numeric'`), ensure the environment (versions of pandas, numpy, scipy, etc.) on the host exactly match those inside the container's `requirements.txt`.
