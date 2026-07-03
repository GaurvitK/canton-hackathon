from decimal import Decimal

from common import *


def main():
    tok = token()
    party = party_id()

    acs = active_holdings(tok, party)
    holdings = parse_holdings(acs)

    total = Decimal("0")
    rows = []

    for holding in holdings:
        payload = holding["payload"]
        amount = Decimal(str(payload["amount"]))
        total += amount

        rows.append(
            {
                "contractId": holding["contractId"],
                "amount": str(amount),
                "instrumentId": payload.get("instrumentId"),
                "lock": payload.get("lock"),
            }
        )

    print_json(
        {
            "party_id": party,
            "holding_contracts": len(rows),
            "total_balance": str(total),
            "holdings": rows,
        }
    )


if __name__ == "__main__":
    main()