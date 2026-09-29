import os
import pandas as pd
import numpy as np
import joblib
import logging
import matplotlib.pyplot as plt
import seaborn as sns

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
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')

os.makedirs(os.path.join(MODELS_DIR, 'regression'), exist_ok=True)
os.makedirs(os.path.join(MODELS_DIR, 'classification'), exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# AQI Categories Mapping
AQI_CATEGORIES = ['Good', 'Satisfactory', 'Moderate', 'Poor', 'Very Poor', 'Severe']

def load_data():
    logger.info("Loading datasets...")
    train_df = pd.read_csv(os.path.join(DATA_DIR, 'train', 'train.csv'))
    val_df = pd.read_csv(os.path.join(DATA_DIR, 'validation', 'validation.csv'))
    test_df = pd.read_csv(os.path.join(DATA_DIR, 'test', 'test.csv'))
    
    train_df['date'] = pd.to_datetime(train_df['date'])
    val_df['date'] = pd.to_datetime(val_df['date'])
    test_df['date'] = pd.to_datetime(test_df['date'])
    return train_df, val_df, test_df

def validate_chronological_split(train_df, val_df, test_df):
    logger.info("Validating time-series splits...")
    train_max = train_df['date'].max()
    val_min = val_df['date'].min()
    val_max = val_df['date'].max()
    test_min = test_df['date'].min()
    
    assert train_max < val_min, f"Leakage detected: Train max date {train_max} >= Val min date {val_min}"
    assert val_max < test_min, f"Leakage detected: Val max date {val_max} >= Test min date {test_min}"
    logger.info("Time-series validation passed: No chronological leakage.")

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

def train_and_evaluate_regression(X_train, y_train, X_val, y_val):
    logger.info("Training Regression Models...")
    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest Regressor': RandomForestRegressor(n_estimators=100, random_state=42),
        'XGBoost Regressor': XGBRegressor(n_estimators=100, random_state=42)
    }
    
    results = []
    trained_models = {}
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_val)
        mae = mean_absolute_error(y_val, preds)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        r2 = r2_score(y_val, preds)
        
        results.append({'Model': name, 'MAE': mae, 'RMSE': rmse, 'R2': r2})
        trained_models[name] = model
        
    results_df = pd.DataFrame(results).sort_values('MAE')
    logger.info(f"\nRegression Validation Results:\n{results_df.to_string(index=False)}")
    
    best_model_name = results_df.iloc[0]['Model']
    logger.info(f"Selected Regression Model: {best_model_name}")
    
    return trained_models[best_model_name], results_df

def map_categories_to_int(series):
    # Mapping to integers for models that require numeric classes (like XGBoost)
    cat_map = {cat: i for i, cat in enumerate(AQI_CATEGORIES)}
    return series.map(cat_map), cat_map

def train_and_evaluate_classification(X_train, y_train, X_val, y_val, class_map):
    logger.info("Training Classification Models...")
    
    y_train_num = y_train.map(class_map)
    y_val_num = y_val.map(class_map)
    
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'),
        'Random Forest Classifier': RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'),
        'XGBoost Classifier': XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)
    }
    
    results = []
    trained_models = {}
    
    for name, model in models.items():
        model.fit(X_train, y_train_num)
        preds_num = model.predict(X_val)
        
        acc = accuracy_score(y_val_num, preds_num)
        prec = precision_score(y_val_num, preds_num, average='macro', zero_division=0)
        rec = recall_score(y_val_num, preds_num, average='macro', zero_division=0)
        f1_macro = f1_score(y_val_num, preds_num, average='macro', zero_division=0)
        f1_weighted = f1_score(y_val_num, preds_num, average='weighted', zero_division=0)
        
        results.append({
            'Model': name, 'Accuracy': acc, 'Macro Precision': prec, 
            'Macro Recall': rec, 'Macro F1': f1_macro, 'Weighted F1': f1_weighted
        })
        trained_models[name] = model
        
    results_df = pd.DataFrame(results).sort_values('Macro F1', ascending=False)
    logger.info(f"\nClassification Validation Results:\n{results_df.to_string(index=False)}")
    
    best_model_name = results_df.iloc[0]['Model']
    logger.info(f"Selected Classification Model: {best_model_name}")
    
    return trained_models[best_model_name], results_df

def final_test_evaluation(reg_model, clf_model, X_test, y_reg_test, y_clf_test, class_map):
    logger.info("Performing FINAL TEST EVALUATION exactly once...")
    
    # Regression Test
    reg_preds = reg_model.predict(X_test)
    reg_mae = mean_absolute_error(y_reg_test, reg_preds)
    reg_rmse = np.sqrt(mean_squared_error(y_reg_test, reg_preds))
    reg_r2 = r2_score(y_reg_test, reg_preds)
    
    # Classification Test
    y_clf_test_num = y_clf_test.map(class_map)
    clf_preds_num = clf_model.predict(X_test)
    
    clf_acc = accuracy_score(y_clf_test_num, clf_preds_num)
    clf_prec = precision_score(y_clf_test_num, clf_preds_num, average='macro', zero_division=0)
    clf_rec = recall_score(y_clf_test_num, clf_preds_num, average='macro', zero_division=0)
    clf_f1_macro = f1_score(y_clf_test_num, clf_preds_num, average='macro', zero_division=0)
    clf_f1_weighted = f1_score(y_clf_test_num, clf_preds_num, average='weighted', zero_division=0)
    
    test_results_text = f"""FINAL TEST METRICS
====================
Regression:
MAE: {reg_mae:.4f}
RMSE: {reg_rmse:.4f}
R2: {reg_r2:.4f}

Classification:
Accuracy: {clf_acc:.4f}
Macro Precision: {clf_prec:.4f}
Macro Recall: {clf_rec:.4f}
Macro F1: {clf_f1_macro:.4f}
Weighted F1: {clf_f1_weighted:.4f}
"""
    logger.info("\n" + test_results_text)
    
    with open(os.path.join(REPORTS_DIR, 'test_results.txt'), 'w') as f:
        f.write(test_results_text)
        
    # Regression Plot
    plt.figure(figsize=(10, 6))
    plt.scatter(y_reg_test, reg_preds, alpha=0.5)
    plt.plot([y_reg_test.min(), y_reg_test.max()], [y_reg_test.min(), y_reg_test.max()], 'r--')
    plt.xlabel('Actual Next-Day AQI')
    plt.ylabel('Predicted Next-Day AQI')
    plt.title('Regression: Actual vs Predicted (Test Set)')
    plt.savefig(os.path.join(REPORTS_DIR, 'regression_actual_vs_predicted.png'))
    plt.close()
    
    # Classification Confusion Matrix Plot
    cm = confusion_matrix(y_clf_test_num, clf_preds_num, labels=range(len(AQI_CATEGORIES)))
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=AQI_CATEGORIES, yticklabels=AQI_CATEGORIES)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Classification: Confusion Matrix (Test Set)')
    plt.savefig(os.path.join(REPORTS_DIR, 'confusion_matrix.png'))
    plt.close()

def main():
    train_df, val_df, test_df = load_data()
    validate_chronological_split(train_df, val_df, test_df)
    
    logger.info(f"Train size: {len(train_df)}, Val size: {len(val_df)}, Test size: {len(test_df)}")
    
    X_train_raw, y_reg_train, y_clf_train = prepare_features_and_targets(train_df)
    X_val_raw, y_reg_val, y_clf_val = prepare_features_and_targets(val_df)
    X_test_raw, y_reg_test, y_clf_test = prepare_features_and_targets(test_df)
    
    logger.info("Fitting Preprocessing Pipeline (Imputation + Scaling) on TRAIN ONLY...")
    preprocessor = build_preprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)
    X_test = preprocessor.transform(X_test_raw)
    
    joblib.dump(preprocessor, os.path.join(MODELS_DIR, 'regression', 'preprocessing.joblib'))
    joblib.dump(preprocessor, os.path.join(MODELS_DIR, 'classification', 'preprocessing.joblib'))
    
    # Train & Select Regression
    best_reg_model, reg_val_results = train_and_evaluate_regression(X_train, y_reg_train, X_val, y_reg_val)
    reg_val_results.to_csv(os.path.join(REPORTS_DIR, 'regression_results.csv'), index=False)
    joblib.dump(best_reg_model, os.path.join(MODELS_DIR, 'regression', 'selected_regression_model.joblib'))
    
    # Train & Select Classification
    _, class_map = map_categories_to_int(y_clf_train)
    best_clf_model, clf_val_results = train_and_evaluate_classification(X_train, y_clf_train, X_val, y_clf_val, class_map)
    clf_val_results.to_csv(os.path.join(REPORTS_DIR, 'classification_results.csv'), index=False)
    joblib.dump(best_clf_model, os.path.join(MODELS_DIR, 'classification', 'selected_classification_model.joblib'))
    # Save the class map to inverse transform later
    joblib.dump(class_map, os.path.join(MODELS_DIR, 'classification', 'class_map.joblib'))
    
    # Evaluate exactly ONCE on Test Set
    final_test_evaluation(best_reg_model, best_clf_model, X_test, y_reg_test, y_clf_test, class_map)
    
    logger.info("Phase 2 Model Training and Evaluation Complete.")

if __name__ == "__main__":
    main()
