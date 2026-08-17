SECTION 1 - Workflow
1. First we receive the first message, save it to a DB, then we call the LLM API
2. Then the LLM gives us what to execute. An example will be like `I need look_up_transaction()`.
3. Then we execute the SQL and give the details to the LLM
4. LLM found 3 somewhat similar transactions, so LLM gave us the message to forward to the claimer "Bro, which transaction among these 3?". First we save our response to DB and then we message the claimer.
5. Then the claimer points at one transaction and we update the DB.
6. Then we forward it to the LLM.
7. The LLM identifies the transaction and asks us to run our Fraud ML model on that transaction. We do it and tell the LLM the fraud score.
8. Case 1 - Confident Fraud: LLM asks us to convey. Then we save our message to the DB and we file a dispute. Then convey the claimer to calm down and everything has been taken care of. No human is in the loop.
9. Case 2 - Confident Not-Fraud: LLM asks us to convey "Bro don't bluff, okay?". Same as above, we save our response to the DB and then message the claimer.
10. Case 3 - Not confident: LLM tells us it is not confident and asks us that pass_over_to_humans queue should be invoked. We also get the reasons the Fraud ML model is not confident and attach those details in the ticket. Then we save that decision too to DB and we pass it over to humans.

SECTION 2 - Database Tables
1. conversations: created_at, conversation_id, person_id, status
2. messages: created_at, message_id, conversation_id, sender_id, message_text
3. transactions: transaction_id, transaction_amount, merchant_id, card_id, transaction_time, status_of_transaction, payment method (online or offline)
4. merchants: created_at, merchant_id, merchant_name, other merchant details like address, latitude, risk_flag
5. cardholders: created_at, person_id, person_name, other personal details like address, annual salary, etc
6. cards: created_at, card_id, person_id, card_no_last4, name_on_card, billing_address, provider
7. previous fraud model scores: created_at, model_run_id, transaction_id, fraud_score, model_version
8. disputes: created_at, dispute_id, transaction_id with a UNIQUE constraint, claim_reason, escalation_reason, status

SECTION 3 - Functions
1. `look_up_transactions(person_id, amount = None, merchant = None, date = None)` function - Takes the arguments from the session/login data. If the count is 1, this returns the transaction details. If the count is more than 1, this function should return all those transactions matching (of course of this person only)
2. `score_fraud(transaction_id)` function - Scores the fraud and then outputs the 0.0 - 1.0 chance of that transaction being fraud.
3. `file_dispute(transaction_id, claim_reason)` function - Creates a new record in the database of disputes. Should never be able to file a dispute for another client. Only the logged in customer should be able to file his dispute with our tool's help.
4. `escalate(dispute_id, transaction_id, escalation_reason)` function - Pushes the dispute to a human review. So the dispute details are included.

SECTION 4 - Failure cases
1. Prompt Injection - We remove the LLM refunding automatically altogether. All the LLM does is reason our chatbot's way into seeing if the transaction is fraud or not and what needs to be done.
2. Person Dishonesty - Customers can try to make a huge transaction, get the benefits and then claim it as fraud and fool the LLM into refunding them the money. We need to tackle this. If this can be flagged uncertain, then it's great, a human will review it.
3. Hallucination - The LLMs can make up function names, table names or just stop creating the dispute and think it already did it, etc.
4. Double Filing - We can use UNIQUE  constraint on the transaction_id in the DB. So even if there is a network lag etc., we can prevent filing 2 disputes for one transaction.
5. If there ar multiple transactions sitting closely, then the LLM should confirm the exact transaction with the person before filing a dispute.
6. Reassure the customer everything is taken care of when nothing yet is done
7. Infinite call loop. We keep a limit of 5 or 6 tool calls, which is more than enough.

NOTES -
1. Identity of the person should always come from login data and never from the LLM or the person, to ensure privacy of other transactions. Model-supplied arguments never carry identity or facts, only references, and the server resolves them inside the caller's scope.
2. LLM should never ever say PII at all. Hands down. Always a standing rule. 