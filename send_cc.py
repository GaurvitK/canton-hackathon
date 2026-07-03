import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from common import *


def iso(dt):
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def transfer_context(tok, sender, receiver, amount):
    holdings = parse_holdings(active_holdings(tok, sender))

    if not holdings:
        raise SystemExit("No Holding contracts found.")

    instrument = holdings[0]["payload"]["instrumentId"]
    admin = instrument["admin"]
    token_id = instrument["id"]

    needed = Decimal(amount)

    selected = []
    available = Decimal("0")

    for holding in sorted(
        holdings,
        key=lambda x: Decimal(str(x["payload"]["amount"])),
    ):
        payload = holding["payload"]

        if payload.get("instrumentId") != {"admin": admin, "id": token_id}:
            continue

        if payload.get("lock") is not None:
            continue

        selected.append(holding)
        available += Decimal(str(payload["amount"]))

        if available >= needed:
            break

    if available < needed:
        raise SystemExit(f"Insufficient unlocked balance: {available} < {needed}")

    now = datetime.now(timezone.utc)

    choice_args = {
        "expectedAdmin": admin,
        "transfer": {
            "sender": sender,
            "receiver": receiver,
            "amount": str(needed),
            "instrumentId": {
                "admin": admin,
                "id": token_id,
            },
            "lock": None,
            "requestedAt": iso(now - timedelta(minutes=2)),
            "executeBefore": iso(now + timedelta(hours=24)),
            "inputHoldingCids": [h["contractId"] for h in selected],
            "meta": {
                "values": {
                    "splice.lfdecentralizedtrust.org/reason": "Canton hackathon transfer"
                }
            },
        },
        "extraArgs": {
            "context": {
                "values": {}
            },
            "meta": {
                "values": {}
            },
        },
    }

    response = post(
        tok,
        f"{VALIDATOR_API}/v0/scan-proxy/registry/transfer-instruction/v1/transfer-factory",
        {
            "choiceArguments": choice_args,
            "excludeDebugFields": True,
        },
    )

    choice_args["extraArgs"]["context"] = response["choiceContext"]["choiceContextData"]

    return {
        "factoryId": response["factoryId"],
        "choiceArguments": choice_args,
        "disclosedContracts": response["choiceContext"].get("disclosedContracts", []),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receiver", required=True)
    parser.add_argument("--amount", required=True)
    args = parser.parse_args()

    tok = token()
    sender = party_id()

    ctx = transfer_context(
        tok=tok,
        sender=sender,
        receiver=args.receiver,
        amount=args.amount,
    )

    command = {
        "ExerciseCommand": {
            "templateId": TRANSFER_FACTORY_INTERFACE,
            "contractId": ctx["factoryId"],
            "choice": "TransferFactory_Transfer",
            "choiceArgument": ctx["choiceArguments"],
        }
    }

    result = submit_external(
        tok,
        sender,
        command,
        disclosed_contracts=ctx["disclosedContracts"],
    )

    print("SUCCESS: Transfer submitted")
    print_json(result)


if __name__ == "__main__":
    main()