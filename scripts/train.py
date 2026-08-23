import csv
import json
import os
from datetime import datetime

import torch
from sklearn.metrics import average_precision_score
from torch import nn

# Claude-built per the PYTORCH MODEL EXCEPTION (Kalyan 2026-08-21): the schedule
# overflowed so this one script was finished by Claude, not typed by hand. When
# Kalyan learns PyTorch properly he re-builds it himself and archives this version.
# It keeps his beginner-readable style on purpose: plain loops, no clever wrappers.

# Paths are anchored to this file so the script runs the same from any folder.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
MODELS = os.path.join(ROOT, "models")
os.makedirs(MODELS, exist_ok=True)

# The 14 real Sparkov category values. We read them from the train CSV so the
# order is fixed and reproducible, then one-hot encode against this list. Only
# real signals feed the model: amt, hour, category. No invented columns.
categories = set()
with open(os.path.join(DATA, "credit_card_transaction_train.csv")) as f:
    for row in csv.DictReader(f):
        categories.add(row["category"])
categories = sorted(categories)
print("categories:", categories)


def make_features(row):
    # First two numbers are amt and the hour of day. The rest is a one-hot block:
    # a 1 in the slot for this row's category and 0 everywhere else.
    amt = float(row["amt"])
    hour = datetime.strptime(row["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S").hour  # noqa: DTZ007
    one_hot = [0.0] * len(categories)
    one_hot[categories.index(row["category"])] = 1.0
    return [amt, float(hour)] + one_hot


with open(os.path.join(DATA, "credit_card_transaction_train.csv")) as f:
    features, labels = [], []
    for row in csv.DictReader(f):
        features.append(make_features(row))
        labels.append(float(row["is_fraud"]))

X = torch.tensor(features)
y = torch.tensor(labels)

# Scale amt and hour only (the first two columns). Mean and sd are computed on
# the train set alone, then reused on test. The one-hot columns are already 0/1
# and must stay untouched, so we scale a slice and leave the rest alone.
means = X[:, :2].mean(dim=0)
sds = X[:, :2].std(dim=0)
X[:, :2] = (X[:, :2] - means) / sds

dataset = torch.utils.data.TensorDataset(X, y)
loader = torch.utils.data.DataLoader(dataset, batch_size=1024, shuffle=True)

# Net input is 2 scaled numbers plus one slot per category.
n_features = 2 + len(categories)
model = nn.Sequential(nn.Linear(n_features, 16), nn.ReLU(), nn.Linear(16, 1))

# Fraud is about 0.4% of rows, so we tell the loss to weight the rare positives.
pos_weight = (y == 0).sum() / (y == 1).sum()
loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# Load the test set once so we can print an AUPRC after every epoch and watch it
# climb. Same feature build, same scaling with the train means and sds.
with open(os.path.join(DATA, "credit_card_transaction_test.csv")) as g:
    test_features, test_labels = [], []
    for row in csv.DictReader(g):
        test_features.append(make_features(row))
        test_labels.append(float(row["is_fraud"]))

X_test = torch.tensor(test_features)
y_test = torch.tensor(test_labels)
X_test[:, :2] = (X_test[:, :2] - means) / sds

epochs = 20
for epoch in range(epochs):
    model.train()
    for xb, yb in loader:
        preds = model(xb).squeeze(1)
        loss = loss_fn(preds, yb)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        test_scores = model(X_test).squeeze(1)
    auprc = average_precision_score(y_test, test_scores)
    print(f"epoch {epoch} loss {loss.item():.4f} test_auprc {auprc:.4f}")

# Save everything score_fraud needs to rebuild a feature vector and run the net:
# the trained weights, the scaling numbers, and the frozen category order.
# The scaler and category list also go to JSON so the app can score with only
# onnxruntime and no torch import.
torch.save(model.state_dict(), os.path.join(MODELS, "fraud_model.pt"))
torch.save({"means": means, "sds": sds}, os.path.join(MODELS, "scaler.pt"))
with open(os.path.join(MODELS, "scaler.json"), "w") as f:
    json.dump({"means": means.tolist(), "sds": sds.tolist()}, f)
with open(os.path.join(MODELS, "categories.json"), "w") as f:
    json.dump(categories, f)

# Export the same net to ONNX so the app can score with onnxruntime and no torch.
model.eval()
dummy = torch.zeros(1, n_features)
torch.onnx.export(
    model,
    dummy,
    os.path.join(MODELS, "fraud_model.onnx"),
    input_names=["features"],
    output_names=["logit"],
    dynamic_axes={"features": {0: "batch"}, "logit": {0: "batch"}},
    dynamo=False,
)
print("saved model, scaler, categories, and onnx to", MODELS)
