"""
CyberSentinel Model Training & Evaluation Engine
Trains:
  1. Isolation Forest (Anomaly Baseline)
  2. Hotspot Risk Classifier & Ranker (Target 1: future_cashout)
  3. Withdrawal Volume Regressor (Target 2: future_withdrawal_volume)
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, silhouette_score,
    mean_absolute_error, root_mean_squared_error
)

from src.features import load_feature_splits
from src.preprocessing import preprocess_pipeline

def train_and_evaluate_model():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    synthetic_csv = os.path.join(base_dir, 'data', 'synthetic', 'synthetic_historical_ml_dataset.csv')
    processed_dir = os.path.join(base_dir, 'data', 'processed')
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)

    # 1. Preprocess if splits do not exist
    train_file = os.path.join(processed_dir, 'train_data.csv')
    val_file = os.path.join(processed_dir, 'val_data.csv')
    test_file = os.path.join(processed_dir, 'test_data.csv')

    if not (os.path.exists(train_file) and os.path.exists(val_file) and os.path.exists(test_file)):
        print("\n[Step 1/4] Running preprocessing pipeline on synthetic dataset...")
        preprocess_pipeline(synthetic_csv, processed_dir)

    # 2. Load Feature Splits
    print("\n[Step 2/4] Loading feature matrices from processed splits...")
    (X_train, y_tr_hotspot, y_tr_vol), (X_val, y_val_hotspot, y_val_vol), (X_test, y_te_hotspot, y_te_vol), feature_names = load_feature_splits(processed_dir)

    print(f"  Features : {len(feature_names)}")
    print(f"  Train    : {len(X_train):,} samples (70%)")
    print(f"  Val      : {len(X_val):,} samples (15%)")
    print(f"  Test     : {len(X_test):,} samples (15%)")

    # 3. Model 1: Isolation Forest (Anomaly baseline)
    print("\n[Step 3/4] Training Models...")
    print("  -> Training Isolation Forest Anomaly Detector...")
    iso_forest = IsolationForest(n_estimators=200, contamination=0.15, random_state=20260923, n_jobs=-1)
    iso_forest.fit(X_train)

    # 4. Model 2: Hotspot Risk Classifier & Ranker (Target 1: future_cashout)
    print("  -> Training Hotspot Risk Classifier (HistGradientBoosting + Isotonic Calibration)...")
    base_clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, random_state=20260923)
    hotspot_model = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
    hotspot_model.fit(X_train, y_tr_hotspot)

    # 5. Model 3: Withdrawal Volume Regressor (Target 2: future_withdrawal_volume)
    print("  -> Training Withdrawal Volume Regressor (HistGradientBoostingRegressor)...")
    volume_model = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, random_state=20260923)
    volume_model.fit(X_train, y_tr_vol)

    # 6. Evaluation on Test Set
    print("\n[Step 4/4] Evaluating models on unseen Test Set...")
    print("=" * 60)
    print("  MODEL EVALUATION REPORT (TEST SET)")
    print("=" * 60)
    
    # 6a. Unsupervised Isolation Forest Evaluation
    iso_preds = iso_forest.predict(X_test)
    sil_score = float(silhouette_score(X_test, iso_preds, sample_size=min(2000, len(X_test)), random_state=20260923))

    # 6b. Supervised Hotspot Classifier Evaluation
    raw_probs = hotspot_model.predict_proba(X_test)
    probs = raw_probs[:, 1] if raw_probs.shape[1] > 1 else raw_probs[:, 0]

    roc_auc = float(roc_auc_score(y_te_hotspot, probs))
    pr_auc = float(average_precision_score(y_te_hotspot, probs))

    # Top-K Ranking Metrics (Precision@10)
    top10_idx = np.argsort(probs)[-10:]
    top10_actual = y_te_hotspot.iloc[top10_idx]
    #prec_at_10 = float(top10_actual.mean())

    # 6c. Volume Regressor Evaluation
    vol_preds = np.maximum(0, volume_model.predict(X_test))
    #mae = float(mean_absolute_error(y_te_vol, vol_preds))
    #rmse = float(root_mean_squared_error(y_te_vol, vol_preds))

    print(f"  [Unsupervised Anomaly Model Metrics]")
    print(f"    Silhouette Score   : {sil_score:.4f}")
    print(f"\n  [Hotspot Risk Classifier Metrics]")
    print(f"    ROC-AUC Score      : {roc_auc:.4f}")
    print(f"    PR-AUC Score       : {pr_auc:.4f}")
    #print(f"    Precision@10       : {prec_at_10:.4f}")
    print(f"\n  [Withdrawal Volume Forecast Metrics]")
    #print(f"    MAE                : INR {mae:,.2f}")
    #print(f"    RMSE               : INR {rmse:,.2f}")

    # 7. Persist Artifacts
    artifact_payload = {
        'model': iso_forest,
        'hotspot_model': hotspot_model,
        'volume_model': volume_model,
        'feature_names': feature_names,
        'model_version': 'cybersentinel_v1_synthetic',
        'metrics': {
            'silhouette_score': sil_score,
            'roc_auc': roc_auc,
            'pr_auc': pr_auc,
            #'precision_at_10': prec_at_10,
            #'volume_mae': mae,
            #'volume_rmse': rmse
        }
    }
    model_path = os.path.join(models_dir, 'model.pkl')
    joblib.dump(artifact_payload, model_path)
    print(f"\n[OK] Model artifact successfully saved to: {model_path} ({os.path.getsize(model_path) / 1024:.1f} KB)")
    print("=" * 60)

if __name__ == '__main__':
    train_and_evaluate_model()
