# ChargeBack

ChargeBack is a work-in-progress assistant for card-fraud dispute workflows. It is built around a FastAPI chat service, PostgreSQL, and a tool-calling loop.

## Current scope

- Streams chat responses over Server-Sent Events and keeps multi-turn conversation history in PostgreSQL.
- Uses tools for transaction lookup, fraud scoring, and dispute filing.
- Stores each tool call's inputs, result, start time, and latency in a trace table.
- Uses a nine-table PostgreSQL model for cardholders, cards, merchants, transactions, fraud checks, disputes, messages, conversations, and traces.
- Includes a seven-case evaluation runner that replays dispute conversations and checks expected dispute records and tool traces.
- Enforces ownership checks, duplicate-dispute prevention, and two score-policy thresholds in the dispute-filing path.

## In progress

The PyTorch fraud scorer is finished on the branch `22-finish-the-fraud-model`: trained on the transaction data with one-hot merchant categories, 0.74 test AUPRC, exported to ONNX, and wired into `score_fraud`. Until that branch is merged, `main` still carries the random stub. The CI gate, deployment, and grounding work will be documented here only after each is implemented and tested.
