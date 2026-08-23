import json
import math
import os
from datetime import datetime
from decimal import Decimal

import asyncpg
import numpy as np
import onnxruntime

REFUSE_BELOW = 0.33
AUTO_FILE_ABOVE = 0.67

# The fraud model is trained in scripts/train.py and saved under models/. We load
# it once on first use (not on every call) and cache the pieces score_fraud needs:
# the onnxruntime session for the net, the scaling numbers, and the category order.
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
_session = None
_means = None
_sds = None
_categories = None


def _load_model():
    global _session, _means, _sds, _categories
    if _session is not None:
        return
    _session = onnxruntime.InferenceSession(os.path.join(_MODELS_DIR, "fraud_model.onnx"))
    with open(os.path.join(_MODELS_DIR, "scaler.json")) as f:
        scaler = json.load(f)
    _means = scaler["means"]
    _sds = scaler["sds"]
    with open(os.path.join(_MODELS_DIR, "categories.json")) as f:
        _categories = json.load(f)


async def look_up_transactions(conn, person_id, merchant_name=None, amount=None, date=None, card_last4=None):
    query = "SELECT * FROM transactions WHERE card_id IN (SELECT card_id FROM cards WHERE person_id = $1) "
    values = [person_id]

    if merchant_name is not None:
        query += "AND merchant_id IN (SELECT merchant_id FROM merchants WHERE merchant_name ILIKE $" + str(len(values) + 1) + ") "
        values.append(merchant_name)

    if amount is not None:
        query += "AND transaction_amount = $" + str(len(values) + 1) + " "
        values.append(Decimal(str(amount)))

    if date is not None:
        date = datetime.strptime(date, "%Y-%m-%d").date() #noqa: DTZ007
        query += "AND DATE(transaction_time) = $" + str(len(values) + 1) + " "
        values.append(date)

    if card_last4 is not None:
        query += "AND card_id IN (SELECT card_id FROM cards WHERE card_no_last4 = $" + str(len(values) + 1) + ") "
        values.append(card_last4)

    rows = await conn.fetch(
        query, *values
    )

    return rows

async def score_fraud(conn, transaction_id):
    _load_model()

    row = await conn.fetchrow(
        "SELECT transaction_amount, transaction_time, category FROM transactions WHERE transaction_id = $1",
        transaction_id,
    )

    # Build the same feature vector the model trained on: amt and hour scaled with
    # the saved means and sds, then a one-hot block for the transaction category.
    amt = (float(row["transaction_amount"]) - _means[0]) / _sds[0]
    hour = (float(row["transaction_time"].hour) - _means[1]) / _sds[1]
    one_hot = [0.0] * len(_categories)
    one_hot[_categories.index(row["category"])] = 1.0

    features = np.array([[amt, hour, *one_hot]], dtype=np.float32)
    logit = _session.run(None, {"features": features})[0][0][0]

    # The net outputs a raw logit, so squash it to a 0-1 probability with sigmoid.
    return float(1 / (1 + math.exp(-float(logit))))

async def file_dispute(conn, person_id, transaction_id, claim_reason, escalation_reason=None) -> str:
    # Check if the transaction_id belongs to person_id or not, once more.
    person_really = await conn.fetchval(
        "SELECT person_id FROM cards WHERE card_id IN"
        "(SELECT card_id FROM transactions WHERE transaction_id = $1)", transaction_id
    )
    if person_really != person_id:
        return "Person IDs not matching. Investigate further"

    score = await score_fraud(conn, transaction_id)
    # Will get to this double calling again. Claude, remind me regarding this


    if score < REFUSE_BELOW:
        return "Sorry, I cannot help with this. Please contact Chargeback Customer Care for further assistance."
    else:
        try:
            await conn.execute(
            "INSERT INTO disputes (transaction_id, claim_reason, escalation_reason) VALUES ($1, $2, $3)", transaction_id, claim_reason, escalation_reason
            )
        except asyncpg.UniqueViolationError:
            return "A dispute for this transaction already exists."

        if score < AUTO_FILE_ABOVE:
            return "I'm going to have to escalate this dispute and humans will be reaching out to you soon regarding further assistance."
        else:
            return "Don't worry, I took care of it and a dispute has been filed. Very soon, we will reach out regarding further process."