# ChargeBack

ChargeBack is a work-in-progress AI assistant for card-fraud disputes. It finds a transaction, scores it and applies server-side filing rules. PostgreSQL keeps the conversation, tool traces and dispute records.

## Follow one request

```text
POST /chat → FastAPI → Bedrock tool-calling loop → streamed reply
                           ↓
             transaction lookup → ONNX fraud score → filing policy
                           ↓
              PostgreSQL: messages, traces and disputes
```

- [Chat service](app/main.py): streams text over Server-Sent Events and reloads multi-turn history.
- [Agent loop](app/llm.py): calls transaction lookup, fraud scoring and dispute filing. Records each tool's inputs, result, start time and latency.
- [Filing policy](app/tools.py): rechecks ownership and score before inserting a dispute. Scores below 0.33 refuse filing; 0.33 to below 0.67 return an escalation outcome; 0.67 or higher return a filed outcome. A unique constraint prevents duplicate disputes.
- [Schema](db/schema.sql): nine tables covering cardholders, cards, merchants, transactions, fraud checks, disputes, messages, conversations and traces.

The [PyTorch scorer](scripts/train.py) uses transaction amount, hour and one-hot merchant categories. The recorded training result is **0.74 test AUPRC** (area under the precision-recall curve). It exports to ONNX for `score_fraud`; that result is not a workflow pass rate or a production guarantee.

[Explore the synthetic policy demo](https://kalyanvenk.com/chargeback/) · [Backend recording checklist](docs/demo.md)

## Run locally

Python 3.12+, uv, Docker and AWS credentials with access to the model in [app/llm.py](app/llm.py) are required. The current runtime uses Bedrock in `us-east-1`; chat requests incur model charges.

Data and trained models are not bundled. Supply the original Sparkov-format CSVs as `data/credit_card_transaction_train.csv` and `data/credit_card_transaction_test.csv`. Restore `models/fraud_model.onnx`, `models/scaler.json` and `models/categories.json` from the same training run, or regenerate them with `uv run --locked python scripts/train.py`. Retraining need not reproduce exactly 0.74.

Run these commands from the repository root. This creates a separate local database on port **55432**, not the Compose database on 5432. If the container name already exists, stop and inspect it rather than replacing it.

```sh
uv sync --locked
docker run --name chargeback-demo \
  -e POSTGRES_USER=chargeback \
  -e POSTGRES_PASSWORD=chargeback_demo_local \
  -e POSTGRES_DB=chargeback_demo \
  -p 127.0.0.1:55432:5432 \
  --mount "type=bind,src=$PWD/db/schema.sql,dst=/docker-entrypoint-initdb.d/schema.sql,readonly" \
  -d postgres:16
docker exec chargeback-demo pg_isready -U chargeback -d chargeback_demo
export DATABASE_URL=postgresql://chargeback:chargeback_demo_local@127.0.0.1:55432/chargeback_demo
```

Wait for PostgreSQL to accept connections. The next command **replaces cardholder and merchant data with cascading deletion of related records**. Run it only against this disposable database. It loads the test CSV and generates synthetic salary/provider values.

```sh
uv run --locked python scripts/etl.py
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, a free liveness check:

```sh
curl --fail http://127.0.0.1:8000/health
```

Expected: `{"status":"okay"}`. This endpoint does not validate model access or database contents.

For a **paid** chat request, first select a transaction belonging to demo person 1. Substitute its exact details:

```sh
curl --fail -N http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"I do not recognize the charge of AMOUNT at MERCHANT on YYYY-MM-DD."}'
```

The first event contains `conversation_id`; subsequent events contain text. Include that ID in later requests to continue the conversation. See the [recording checklist](docs/demo.md) for database evidence, not just an agent's claim of success.

## Tests and evaluations

**Free, no database required:**

```sh
uv run --locked pytest tests/test_evals.py tests/test_health.py -q
```

**Paid workflow evaluations:** with the disposable database seeded above and AWS model access configured:

```sh
uv run --locked python -m evals.run_evals
```

The [seven golden cases](evals/goldens) check conversation outcomes, dispute records and tool traces. They substitute fixed fraud scores, so they test workflow behavior rather than the trained scorer's quality. The runner **truncates conversations, messages, disputes and traces before each case**. Never use retained data.

Do not run unrestricted `pytest` casually: `tests/test_chat.py` also resets tables and makes model calls; `tests/conftest.py` selects `chargeback_test` on port 5432 independently of the setup above.

## Current limits

This is a local prototype, not a deployed banking service. `/chat` currently uses demo person 1; authentication is unfinished. An escalation response does not establish a human-review service. Response grounding, evaluation CI gates and cloud deployment remain in progress. The existing GitHub workflow runs lint only.

Validation on 21 September 2026: 19 free tests passed in the existing environment. Clean setup, trained-model inference and a live recorded conversation still need verification with the missing data/model artifacts and a running database.
