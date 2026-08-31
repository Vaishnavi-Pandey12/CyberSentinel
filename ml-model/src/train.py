import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

from features import load_feature_splits
from preprocessing import preprocess_pipeline

# ── Timing Helper ──────────────────────────────────────────────────────────────
def _fmt(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s"

class Timer:
    """Simple step-level timer that prints elapsed and estimated remaining time."""
    def __init__(self, total_steps: int):
        self.total   = total_steps
        self.step    = 0
        self.start   = time.time()
        self._steps  = []

    def tick(self, label: str):
        now = time.time()
        self.step += 1
        elapsed = now - self.start
        avg_per_step = elapsed / self.step
        remaining    = avg_per_step * (self.total - self.step)
        bar_done = int(20 * self.step / self.total)
        bar = "#" * bar_done + "-" * (20 - bar_done)
        print(f"\n  [{bar}] Step {self.step}/{self.total}  |  "
              f"Elapsed: {_fmt(elapsed)}  |  "
              f"ETA: {_fmt(remaining) if self.step < self.total else '-'}")
        print(f"  [OK] {label}")
        self._steps.append((label, elapsed))

    def summary(self):
        total_elapsed = time.time() - self.start
        print(f"\n{'='*60}")
        print(f"  Training Pipeline Complete  -  Total time: {_fmt(total_elapsed)}")
        print(f"{'='*60}")


def train_and_evaluate_model(force_reprocess: bool = False, contamination: float = 0.02):
    """
    Trains an unsupervised Isolation Forest on Indian banking features
    to detect anomalous withdrawal patterns. Displays timing at each step.
    """
    base_dir      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir       = os.path.join(base_dir, 'data', 'raw')
    raw_csv_path  = os.path.join(raw_dir, 'indian_bank_transactions.csv')
    if not os.path.exists(raw_csv_path) and os.path.exists(raw_dir):
        csv_files = [f for f in os.listdir(raw_dir) if f.endswith('.csv')]
        if csv_files:
            raw_csv_path = os.path.join(raw_dir, csv_files[0])
            print(f"Default raw file not found. Auto-detected raw file: {raw_csv_path}")

    processed_dir = os.path.join(base_dir, 'data', 'processed')
    model_dir     = os.path.join(base_dir, 'models')
    model_path    = os.path.join(model_dir, 'model.pkl')

    TOTAL_STEPS = 5
    timer = Timer(TOTAL_STEPS)

    print("=" * 60)
    print("  CyberSentinel — Indian Banking Anomaly Detection")
    print("  Isolation Forest Training Pipeline")
    print("=" * 60)

    # ── Step 1: Preprocess raw data ─────────────────────────────────────────────
    train_csv = os.path.join(processed_dir, 'train_data.csv')
    if force_reprocess or not os.path.exists(train_csv):
        print("\n[Step 1/5] Running preprocessing pipeline on Indian dataset...")
        preprocess_pipeline(raw_csv_path, processed_dir, train_ratio=0.80)
    else:
        print("\n[Step 1/5] Processed splits found — skipping preprocessing.")
        print("  (Run with force_reprocess=True to rebuild from raw data)")
    timer.tick("Preprocessing complete")

    # ── Step 2: Load feature splits ─────────────────────────────────────────────
    print("\n[Step 2/5] Loading feature matrices from processed splits...")
    X_train, y_train, X_test, y_test, feature_names = load_feature_splits(processed_dir)
    print(f"  Features : {len(feature_names)}")
    print(f"  Train    : {len(X_train):,} samples  (80%)")
    print(f"  Test     : {len(X_test):,}  samples  (20%)")
    timer.tick("Feature loading complete")

    # ── Step 3: Train Isolation Forest ─────────────────────────────────────────
    print(f"\n[Step 3/5] Training Isolation Forest  "
          f"(n_estimators=300, contamination={contamination*100:.1f}%)...")
    iso_forest = IsolationForest(
        n_estimators=300,
        max_samples='auto',
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    iso_forest.fit(X_train)
    timer.tick("Model training complete")

    # ── Step 4: Evaluate on test set ────────────────────────────────────────────
    print("\n[Step 4/5] Scoring test set & computing evaluation metrics...")
    test_preds    = iso_forest.predict(X_test)
    is_anomaly    = (test_preds == -1).astype(int)
    anomaly_scores= iso_forest.decision_function(X_test)

    num_anomalies = is_anomaly.sum()
    pct           = (num_anomalies / len(X_test)) * 100

    print("\n" + "=" * 60)
    print("  MODEL EVALUATION METRICS REPORT")
    print("=" * 60)
    print(f"  [Anomaly Detection Statistics]")
    print(f"    Total Test Samples    : {len(X_test):,}")
    print(f"    Flagged Anomalies     : {num_anomalies:,} ({pct:.2f}%)")
    print(f"    Anomaly Score Range   : min={anomaly_scores.min():.4f}, max={anomaly_scores.max():.4f}, mean={anomaly_scores.mean():.4f}")

    if y_test is not None:
        risk_scores = -anomaly_scores  # Invert decision function so higher score = higher risk
        prec = precision_score(y_test, is_anomaly, zero_division=0)
        rec  = recall_score(y_test, is_anomaly, zero_division=0)
        f1   = f1_score(y_test, is_anomaly, zero_division=0)
        roc  = roc_auc_score(y_test, risk_scores)
        pr_auc = average_precision_score(y_test, risk_scores)
        cm   = confusion_matrix(y_test, is_anomaly)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        print("\n  [Performance Metrics vs Ground Truth Targets]")
        print(f"    Precision             : {prec:.4f}")
        print(f"    Recall                : {rec:.4f}")
        print(f"    F1 Score              : {f1:.4f}")
        print(f"    ROC-AUC Score         : {roc:.4f}")
        print(f"    PR-AUC Score          : {pr_auc:.4f}")

        print("\n  [Confusion Matrix Breakdown]")
        print(f"    True Negatives  (TN)  : {tn:,}")
        print(f"    False Positives (FP)  : {fp:,}")
        print(f"    False Negatives (FN)  : {fn:,}")
        print(f"    True Positives  (TP)  : {tp:,}")

    # Profile anomalies vs normal
    results_df = X_test.copy()
    results_df['is_anomaly']    = is_anomaly
    results_df['anomaly_score'] = anomaly_scores
    results_df['transaction_amount_actual'] = np.expm1(results_df['log_transaction_amount'])

    profile_cols = [
        'transaction_amount_actual',
        'dist_from_last_txn_km',
        'minutes_since_last_txn',
        'login_attempts',
        'historical_location_risk'
    ]
    profile = results_df.groupby('is_anomaly')[profile_cols].mean().round(2)
    profile.index = ['Normal (0)', 'Anomaly (1)']
    print("\n  [Average Feature Values: Normal vs Anomaly]")
    print("  " + "-" * 54)
    print(profile.T.to_string())
    print("  " + "-" * 54)

    # Export flagged anomalies
    anomalies_df = results_df[results_df['is_anomaly'] == 1].sort_values('anomaly_score')
    export_path  = os.path.join(processed_dir, 'flagged_anomalies_test_set.csv')
    anomalies_df.to_csv(export_path, index=False)
    print(f"\n  Exported {len(anomalies_df):,} flagged anomalies -> {export_path}")
    timer.tick("Evaluation & anomaly export complete")

    # ── Step 5: Save model artifact ─────────────────────────────────────────────
    print(f"\n[Step 5/5] Saving model artifact -> {model_path}")
    os.makedirs(model_dir, exist_ok=True)
    model_payload = {
        'model':             iso_forest,
        'feature_names':     feature_names,
        'contamination_rate': contamination,
        'model_version':     'iso_forest_v1_india'
    }
    joblib.dump(model_payload, model_path)
    print(f"  Saved: {os.path.getsize(model_path) / 1024:.1f} KB")
    timer.tick("Model artifact saved")

    timer.summary()


if __name__ == '__main__':
    train_and_evaluate_model(force_reprocess=False, contamination=0.02)