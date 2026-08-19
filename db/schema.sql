CREATE TABLE cardholders(
    person_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_name TEXT NOT NULL,
    address TEXT NOT NULL,
    annual_salary BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversations (
    conversation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES cardholders(person_id),
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages(
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_text TEXT NOT NULL,
    conversation_id BIGINT NOT NULL REFERENCES conversations(conversation_id),
    sender TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE merchants(
    merchant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    merchant_latitude FLOAT NOT NULL,
    merchant_longitude FLOAT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cards(
    card_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id BIGINT NOT NULL REFERENCES cardholders(person_id),
    card_no_last4 TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transactions(
    transaction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_amount NUMERIC(12,2) NOT NULL,
    merchant_id BIGINT NOT NULL REFERENCES merchants(merchant_id),
    card_id BIGINT NOT NULL REFERENCES cards(card_id),
    transaction_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    category TEXT NOT NULL,
    transaction_status TEXT NOT NULL DEFAULT 'successful',
    is_fraud BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE fraud_checks(
    fraud_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(transaction_id),
    fraud_score FLOAT NOT NULL,
    run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version TEXT NOT NULL
);

CREATE TABLE disputes(
    dispute_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL UNIQUE REFERENCES transactions(transaction_id),
    claim_reason TEXT NOT NULL,
    escalation_reason TEXT,
    status TEXT NOT NULL DEFAULT 'filed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);