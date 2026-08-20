import csv
from datetime import datetime

with open("../data/credit_card_transaction_train.csv") as f:
    training_data = csv.DictReader(f)

    features, labels = [], []
    for row in training_data:
        features.append([float(row["amt"]), datetime.strptime(row["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S").hour])
        labels.append(float(row["is_fraud"]))

    print(len(features))
    print(len(labels))

    print(features[0])
    print(labels[0])