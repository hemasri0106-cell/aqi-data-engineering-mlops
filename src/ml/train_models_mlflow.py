import os
import pandas as pd
import numpy as np
import joblib
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from xgboost import XGBRegressor, XGBClassifier
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix
)

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'ml')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')

# MLflow Configuration
from dotenv import load_dotenv
load_dotenv()
MLFLOW_DB_URI = os.getenv("MLFLOW_TRACKING_URI")
ARTIFACT_LOCATION = f"file:///{PROJECT_ROOT}/mlflow_artifacts"
mlflow.set_tracking_uri(MLFLOW_DB_URI)
os.makedirs(os.path.join(PROJECT_ROOT, 'mlflow_artifacts'), exist_ok=True)

# Define AQI Categories
AQI_CATEGORIES = ['Good', 'Satisfactory', 'Moderate', 'Poor', 'Very Poor', 'Severe']

def create_experiment(name):
    client = MlflowClient()
    experiment = client.get_experiment_by_name(name)
    if experiment is None:
        experiment_id = client.create_experiment(name, artifact_location=ARTIFACT_LOCATION)
    else:
        experiment_id = experiment.experiment_id
    return experiment_id

def load_data():
    train_df = pd.read_csv(os.path.join(DATA_DIR, 'train', 'train.csv'))
    val_df = pd.read_csv(os.path.join(DATA_DIR, 'validation', 'validation.csv'))
    test_df = pd.read_csv(os.path.join(DATA_DIR, 'test', 'test.csv'))
    
    train_df['date'] = pd.to_datetime(train_df['date'])
    val_df['date'] = pd.to_datetime(val_df['date'])
    test_df['date'] = pd.to_datetime(test_df['date'])
    return train_df, val_df, test_df

def prepare_features_and_targets(df):
    X = df.drop(columns=['target_next_day_aqi', 'target_next_day_category', 'date'])
    y_reg = df['target_next_day_aqi']
    y_clf = df['target_next_day_category']
    return X, y_reg, y_clf

def build_preprocessor():
    numeric_features = [
        'pm25', 'no2', 'aqi', 'temperature_c', 'humidity_pct', 'precipitation_mm', 'wind_speed_kmh',
        'day_of_week', 'month',
        'aqi_lag_1', 'aqi_lag_2', 'aqi_lag_3',
        'pm25_lag_1', 'pm25_lag_2', 'pm25_lag_3',
        'no2_lag_1', 'no2_lag_2', 'no2_lag_3',
        'aqi_roll_mean_3d', 'aqi_roll_mean_7d', 'aqi_roll_std_7d',
        'pm25_roll_mean_3d', 'pm25_roll_mean_7d', 'pm25_roll_std_7d',
        'no2_roll_mean_3d', 'no2_roll_mean_7d', 'no2_roll_std_7d'
    ]
    categorical_features = ['station_id', 'city']

    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    return preprocessor

def train_and_track_regression(X_train, y_train, X_val, y_val, exp_id, X_train_raw):
    logger.info("Training and Tracking Regression Models...")
    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest Regressor': RandomForestRegressor(n_estimators=100, random_state=42),
        'XGBoost Regressor': XGBRegressor(n_estimators=100, random_state=42)
    }
    
    results = []
    
    for name, model in models.items():
        with mlflow.start_run(experiment_id=exp_id, run_name=name) as run:
            model.fit(X_train, y_train)
            preds = model.predict(X_val)
            
            mae = mean_absolute_error(y_val, preds)
            rmse = np.sqrt(mean_squared_error(y_val, preds))
            r2 = r2_score(y_val, preds)
            
            # Log Parameters
            mlflow.log_param("model_name", name)
            mlflow.log_param("train_rows", len(X_train))
            mlflow.log_param("feature_count", X_train.shape[1])
            mlflow.log_param("random_seed", 42 if 'Random' in name or 'XGB' in name else None)
            
            # Log Metrics
            mlflow.log_metric("val_mae", mae)
            mlflow.log_metric("val_rmse", rmse)
            mlflow.log_metric("val_r2", r2)
            
            # Log Tags
            mlflow.set_tags({
                "project": "AQI Prediction",
                "part": "Part 2",
                "task": "regression",
                "target": "next_day_aqi",
                "dataset_version": "Phase1_ML_Dataset",
                "split_strategy": "chronological"
            })
            
            # Log Model with Signature
            # We use a small dataframe sample for signature, converting X_train (which is numpy) to DF is tricky, 
            # so we just use the raw feature dataframe sample and the preprocessor inside a pipeline.
            # But the prompt wants us to just log the model. Let's create a sklearn pipeline and log it so it includes preprocessing!
            full_pipeline = Pipeline(steps=[
                ('preprocessor', build_preprocessor()),
                ('model', model)
            ])
            # We refit the full pipeline just for MLflow logging convenience
            full_pipeline.fit(X_train_raw, y_train)
            
            sample_input = X_train_raw.head(3)
            sample_pred = full_pipeline.predict(sample_input)
            signature = infer_signature(sample_input, sample_pred)
            
            mlflow.sklearn.log_model(
                sk_model=full_pipeline,
                artifact_path="model",
                signature=signature,
                input_example=sample_input,
                serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE
            )
            
            results.append({
                'Model': name, 'MAE': mae, 'RMSE': rmse, 'R2': r2, 
                'run_id': run.info.run_id, 'pipeline': full_pipeline
            })
            
    results_df = pd.DataFrame(results).sort_values('MAE')
    best_row = results_df.iloc[0]
    return best_row

def map_categories_to_int(series):
    cat_map = {cat: i for i, cat in enumerate(AQI_CATEGORIES)}
    return series.map(cat_map), cat_map

def train_and_track_classification(X_train_raw, y_train, X_val_raw, y_val, exp_id, class_map):
    logger.info("Training and Tracking Classification Models...")
    
    y_train_num = y_train.map(class_map)
    y_val_num = y_val.map(class_map)
    
    preprocessor = build_preprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)
    
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'),
        'Random Forest Classifier': RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'),
        'XGBoost Classifier': XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)
    }
    
    results = []
    
    for name, model in models.items():
        with mlflow.start_run(experiment_id=exp_id, run_name=name) as run:
            model.fit(X_train, y_train_num)
            preds_num = model.predict(X_val)
            
            acc = accuracy_score(y_val_num, preds_num)
            prec = precision_score(y_val_num, preds_num, average='macro', zero_division=0)
            rec = recall_score(y_val_num, preds_num, average='macro', zero_division=0)
            f1_macro = f1_score(y_val_num, preds_num, average='macro', zero_division=0)
            f1_weighted = f1_score(y_val_num, preds_num, average='weighted', zero_division=0)
            
            # Log Parameters
            mlflow.log_param("model_name", name)
            mlflow.log_param("train_rows", len(X_train))
            mlflow.log_param("feature_count", X_train.shape[1])
            mlflow.log_param("random_seed", 42 if 'Random' in name or 'XGB' in name else None)
            
            # Log Metrics
            mlflow.log_metric("val_accuracy", acc)
            mlflow.log_metric("val_precision", prec)
            mlflow.log_metric("val_recall", rec)
            mlflow.log_metric("val_macro_f1", f1_macro)
            mlflow.log_metric("val_weighted_f1", f1_weighted)
            
            # Log Tags
            mlflow.set_tags({
                "project": "AQI Prediction",
                "part": "Part 2",
                "task": "classification",
                "target": "next_day_category",
                "dataset_version": "Phase1_ML_Dataset",
                "split_strategy": "chronological"
            })
            
            full_pipeline = Pipeline(steps=[
                ('preprocessor', build_preprocessor()),
                ('model', model)
            ])
            full_pipeline.fit(X_train_raw, y_train_num)
            
            sample_input = X_train_raw.head(3)
            sample_pred = full_pipeline.predict(sample_input)
            signature = infer_signature(sample_input, sample_pred)
            
            mlflow.sklearn.log_model(
                sk_model=full_pipeline,
                artifact_path="model",
                signature=signature,
                input_example=sample_input,
                serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE
            )
            
            results.append({
                'Model': name, 'Accuracy': acc, 'Macro F1': f1_macro, 
                'run_id': run.info.run_id, 'pipeline': full_pipeline
            })
            
    results_df = pd.DataFrame(results).sort_values('Macro F1', ascending=False)
    best_row = results_df.iloc[0]
    return best_row

def main():
    train_df, val_df, test_df = load_data()
    
    X_train_raw, y_reg_train, y_clf_train = prepare_features_and_targets(train_df)
    X_val_raw, y_reg_val, y_clf_val = prepare_features_and_targets(val_df)
    X_test_raw, y_reg_test, y_clf_test = prepare_features_and_targets(test_df)
    
    preprocessor = build_preprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)
    
    # 1. Regression
    reg_exp_id = create_experiment("AQI_Next_Day_Regression")
    best_reg = train_and_track_regression(X_train, y_reg_train, X_val, y_reg_val, reg_exp_id, X_train_raw)
    logger.info(f"Selected Regression Model: {best_reg['Model']} with run_id {best_reg['run_id']}")
    
    # 2. Classification
    clf_exp_id = create_experiment("AQI_Next_Day_Classification")
    _, class_map = map_categories_to_int(y_clf_train)
    best_clf = train_and_track_classification(X_train_raw, y_clf_train, X_val_raw, y_clf_val, clf_exp_id, class_map)
    logger.info(f"Selected Classification Model: {best_clf['Model']} with run_id {best_clf['run_id']}")
    
    # 3. Final Test Evaluation - Regression
    logger.info("Evaluating selected regression model on TEST set...")
    reg_pipeline = best_reg['pipeline']
    reg_test_preds = reg_pipeline.predict(X_test_raw)
    
    reg_mae = mean_absolute_error(y_reg_test, reg_test_preds)
    reg_rmse = np.sqrt(mean_squared_error(y_reg_test, reg_test_preds))
    reg_r2 = r2_score(y_reg_test, reg_test_preds)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(y_reg_test, reg_test_preds, alpha=0.5)
    plt.plot([y_reg_test.min(), y_reg_test.max()], [y_reg_test.min(), y_reg_test.max()], 'r--')
    plt.xlabel('Actual Next-Day AQI')
    plt.ylabel('Predicted Next-Day AQI')
    plt.title('Regression: Actual vs Predicted (Test Set)')
    reg_plot_path = os.path.join(REPORTS_DIR, 'mlflow_regression_test_plot.png')
    plt.savefig(reg_plot_path)
    plt.close()
    
    with mlflow.start_run(run_id=best_reg['run_id']):
        mlflow.log_metric("test_mae", reg_mae)
        mlflow.log_metric("test_rmse", reg_rmse)
        mlflow.log_metric("test_r2", reg_r2)
        mlflow.log_artifact(reg_plot_path, artifact_path="plots")
        
        # Register Model
        logger.info("Registering Regression Model...")
        model_uri = f"runs:/{best_reg['run_id']}/model"
        mlflow.register_model(model_uri, "AQI_Next_Day_AQI_Regression")

    # 4. Final Test Evaluation - Classification
    logger.info("Evaluating selected classification model on TEST set...")
    clf_pipeline = best_clf['pipeline']
    y_clf_test_num = y_clf_test.map(class_map)
    clf_test_preds = clf_pipeline.predict(X_test_raw)
    
    clf_acc = accuracy_score(y_clf_test_num, clf_test_preds)
    clf_prec = precision_score(y_clf_test_num, clf_test_preds, average='macro', zero_division=0)
    clf_rec = recall_score(y_clf_test_num, clf_test_preds, average='macro', zero_division=0)
    clf_f1 = f1_score(y_clf_test_num, clf_test_preds, average='macro', zero_division=0)
    clf_f1_weighted = f1_score(y_clf_test_num, clf_test_preds, average='weighted', zero_division=0)
    
    cm = confusion_matrix(y_clf_test_num, clf_test_preds, labels=range(len(AQI_CATEGORIES)))
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=AQI_CATEGORIES, yticklabels=AQI_CATEGORIES)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Classification: Confusion Matrix (Test Set)')
    clf_plot_path = os.path.join(REPORTS_DIR, 'mlflow_classification_test_cm.png')
    plt.savefig(clf_plot_path)
    plt.close()
    
    with mlflow.start_run(run_id=best_clf['run_id']):
        mlflow.log_metric("test_accuracy", clf_acc)
        mlflow.log_metric("test_macro_precision", clf_prec)
        mlflow.log_metric("test_macro_recall", clf_rec)
        mlflow.log_metric("test_macro_f1", clf_f1)
        mlflow.log_metric("test_weighted_f1", clf_f1_weighted)
        mlflow.log_artifact(clf_plot_path, artifact_path="plots")
        
        # Register Model
        logger.info("Registering Classification Model...")
        model_uri = f"runs:/{best_clf['run_id']}/model"
        mlflow.register_model(model_uri, "AQI_Next_Day_Category_Classification")
        
    logger.info("Phase 3 MLflow Tracking Complete.")

if __name__ == "__main__":
    main()
