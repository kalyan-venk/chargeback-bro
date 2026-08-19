from datetime import datetime
from decimal import Decimal


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