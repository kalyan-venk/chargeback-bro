import csv
from datetime import datetime

import torch
from sklearn.metrics import average_precision_score
from torch import nn

with open("../data/credit_card_transaction_train.csv") as f:
    training_data = csv.DictReader(f)

    rows = list(training_data)
    features, labels = [], []

    for row in rows:
        features.append([float(row["amt"]), datetime.strptime(row["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S").hour]) #noqa DTZ007
        labels.append(float(row["is_fraud"]))

    X = torch.tensor(features)
    y = torch.tensor(labels)

    means = X.mean(dim=0)
    sds = X.std(dim=0)
    X = (X - means) / sds

    dataset = torch.utils.data.TensorDataset(X, y)
    loader = torch.utils.data.DataLoader(dataset, batch_size=1024, shuffle=True)

    model = nn.Sequential(nn.Linear(2,8), nn.ReLU(), nn.Linear(8, 1))
    pos_weight = (y==0).sum() / (y==1).sum()
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    for epoch in range(5):
        for xb, yb in loader:
            preds = model(xb).squeeze(1)
            loss = loss_fn(preds, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        print(epoch, loss.item())



with open("../data/credit_card_transaction_test.csv") as g:
    test_data = csv.DictReader(g)

    test_features, test_labels = [], []
    for row in test_data:
        test_features.append([float(row["amt"]), datetime.strptime(row["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S").hour]) #noqa DTZ007
        test_labels.append(float(row["is_fraud"]))

    X_test = torch.tensor(test_features)
    y_test = torch.tensor(test_labels)

    X_test = (X_test - means) / sds

    with torch.no_grad():
        test_scores = model(X_test).squeeze(1)

    print(test_scores[:5])
    print(average_precision_score(y_test, test_scores))