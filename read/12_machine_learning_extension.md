# 12 — Extending to Machine Learning

## Why ML Instead of (or Alongside) Rules?

Our current system uses **rule-based signals** combined into a **weighted ensemble**. This works well and is highly interpretable, but has limitations:

| Rule-Based | Machine Learning |
|------------|-----------------|
| Human experts define what's suspicious | Model learns from labelled data |
| Easy to explain to regulators | Black box (requires SHAP/LIME for explainability) |
| Misses patterns humans didn't think of | Discovers novel patterns automatically |
| Consistent (same inputs → same output) | Can drift as data distribution changes |
| No labelled data needed | Requires ground truth labels |

**Best practice**: Use rules as features for ML, not as replacements. This gives you the best of both worlds.

---

## Option 1: Gradient Boosting (XGBoost / LightGBM)

```python
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

# Features: the signals we already compute are perfect ML features
features = [
    'structuring_score', 'velocity_score', 'funnel_score',
    'graph_pagerank_score', 'graph_cycle_score', 'graph_betweenness_score',
    'tx_count_30d', 'avg_tx_amount', 'unique_counterparties',
    'cash_ratio', 'max_tx_amount',
]

X = df[features].fillna(0)
y = df['is_suspicious']  # ground truth from data generation

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=9,  # 10% positive rate → weight positives 9x
    eval_metric='auc',
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
print(f"AUC-ROC: {auc:.3f}")  # target > 0.90
```

**Advantages for AML:**
- Handles feature interactions automatically (structuring + layering together)
- `feature_importances_` tells you which features matter most
- Explainable with SHAP values for individual predictions
- Works well with imbalanced classes (scale_pos_weight)

---

## Option 2: Graph Neural Networks (GNN)

Traditional rules look at each account in isolation or with simple graph metrics. GNNs can learn complex multi-hop patterns directly from the graph structure.

```python
import torch
import torch_geometric as pyg

# Each node = account, features = [balance, tx_count, avg_amount, ...]
# Each edge = transaction, features = [total_amount, tx_count, days_since_last]

data = pyg.data.Data(
    x    = node_features,    # shape: [n_accounts, n_features]
    edge_index = edge_index, # shape: [2, n_transactions]
    edge_attr  = edge_features,
    y    = labels,           # shape: [n_accounts] — 0 or 1
)

# Graph Attention Network (GAT) — learns which neighbours to pay attention to
class AMLNet(torch.nn.Module):
    def __init__(self, in_channels, hidden, out_channels):
        super().__init__()
        self.conv1 = pyg.nn.GATConv(in_channels, hidden, heads=4, dropout=0.2)
        self.conv2 = pyg.nn.GATConv(hidden * 4, out_channels, heads=1)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return torch.sigmoid(x)  # probability of being suspicious
```

**When to use GNNs:**
- Network has > 100,000 nodes and complex multi-hop patterns
- Simple graph metrics (PageRank, betweenness) don't capture enough
- You have sufficient labelled data (> 10,000 suspicious examples)

---

## Option 3: Anomaly Detection (Unsupervised)

When you DON'T have ground truth labels (common in real AML):

```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Isolation Forest: accounts that are "easy to isolate" are anomalous
iso_forest = IsolationForest(
    contamination=0.10,  # expect ~10% anomalies
    n_estimators=100,
    random_state=42,
)
anomaly_scores = iso_forest.fit_predict(X_scaled)
# -1 = anomalous, +1 = normal
```

**Advantage**: No labels needed — can detect novel typologies not in training data.
**Disadvantage**: High false positive rate; anomalous ≠ suspicious.

---

## Integrating ML into Our Pipeline

Add an ML scoring step after the rule-based signals:

```python
# In pipeline.py, after running rules and graph signals:

# 1. Build feature matrix from signals
feature_df = build_feature_matrix(all_signals, all_accounts)

# 2. Load pre-trained model
model = joblib.load('models/xgb_aml_detector.pkl')

# 3. Get ML probability scores
ml_scores = model.predict_proba(feature_df)[:, 1]

# 4. Blend with rule-based scores (ensemble of ensembles)
RULE_WEIGHT = 0.6
ML_WEIGHT   = 0.4
final_scores = (
    RULE_WEIGHT * rule_based_scores +
    ML_WEIGHT   * ml_scores * 100
)
```

---

## Model Training Pipeline

For production ML in AML, you'd also need:

1. **Feature store**: compute features for all accounts daily, store in a database
2. **Training pipeline**: retrain every quarter with new labelled data (analyst dispositions)
3. **Model versioning**: track which model version produced each score (for audit)
4. **Drift detection**: monitor if the score distribution changes over time
5. **Champion/Challenger**: run two models in parallel, compare performance

---

## Key Metrics for ML-Based AML

| Metric | Target | Why |
|--------|--------|-----|
| AUC-ROC | > 0.90 | Overall discrimination |
| Precision@100 | > 70% | Top alerts are real |
| Recall@Critical | > 95% | Don't miss high-risk accounts |
| FPR@threshold | < 20% | Analyst time is precious |
| Calibration | ECE < 0.05 | Score 75 should mean 75% likely suspicious |

Calibration is particularly important for AML: an analyst should be able to trust that a score of 85 means "this account is very likely suspicious," not just "higher than 80% of other accounts."
