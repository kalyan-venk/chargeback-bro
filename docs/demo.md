# Backend recording

Status: not recorded. Use the [isolated setup](../README.md#run-locally), original trained scorer and a fresh application process. Do not import the evaluation runner: it replaces the scorer with fixed values.

## Before recording

- Confirm the database is `chargeback_demo` on port 55432. Use synthetic records only.
- Restore all three model artifacts from one training run. Never substitute a made-up score and label it live inference.
- Agree a model-call budget before running chat. The current agent loop has no built-in spending cap.
- Hide credentials, account identifiers and unrelated windows. Keep failures visible rather than editing them into apparent success.

Choose a transaction belonging to demo person 1:

```sh
docker exec chargeback-demo psql -U chargeback -d chargeback_demo -c "
SELECT t.transaction_id, t.transaction_amount, m.merchant_name,
       t.transaction_time::date, t.category
FROM transactions t
JOIN cards c USING (card_id)
JOIN merchants m USING (merchant_id)
WHERE c.person_id = 1
ORDER BY t.transaction_id LIMIT 5;"
```

## 60–90-second sequence

1. Show the request with that transaction's exact amount, merchant and date. State: synthetic data, live local backend.
2. Send it through `/chat`. Keep the returned conversation ID and streamed response visible.
3. Inspect the trace for that ID. Show actual lookup/scoring results and any filing call.
4. Inspect the chosen transaction's dispute record. Explain why the actual score led to refusal, escalation or filing. Do not force a favorable outcome.
5. Close with one tradeoff: the model selects tools but server code checks ownership and filing thresholds. One limitation: authentication still uses demo person 1.

In `docker exec -it chargeback-demo psql -U chargeback -d chargeback_demo`, substitute the returned IDs:

```sql
SELECT tool_called, parameters_passed, result, latency_ms
FROM traces WHERE conversation_id = CONVERSATION_ID ORDER BY trace_id;

SELECT dispute_id, transaction_id, claim_reason, escalation_reason, status
FROM disputes WHERE transaction_id = TRANSACTION_ID;
```

A refusal should leave no dispute row. For an escalation, inspect the reason and tool result: the schema defaults `status` to `filed`, so that column alone does not prove human escalation. Persisted messages/traces remain evidence even when filing is refused.

## Publish only after review

Save the recording under `docs/demo/` with its request, commit ID and observed outcome. Review for secrets and factual agreement with the trace. Then link the recording from the README and portfolio; do not replace the synthetic explorer or imply it runs the backend.
