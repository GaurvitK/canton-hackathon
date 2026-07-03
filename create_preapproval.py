from common import *


def validator_party(tok):
    url = f"{VALIDATOR_API}/v0/validator-user"

    try:
        body = get(tok, url, auth=True)
    except Exception:
        body = get(tok, url, auth=False)

    for key in ("party_id", "partyId", "party"):
        if key in body:
            return body[key]

    raise SystemExit(f"Could not find validator party in {body}")


def dso_party(tok):
    body = get(tok, f"{VALIDATOR_API}/v0/scan-proxy/dso-party-id")

    for key in ("dso_party_id", "dsoPartyId", "party_id", "partyId"):
        if key in body:
            return body[key]

    raise SystemExit(f"Could not find DSO party in {body}")


def main():
    tok = token()
    party = party_id()

    command = {
        "CreateCommand": {
            "templateId": PREAPPROVAL_TEMPLATE,
            "createArguments": {
                "receiver": party,
                "provider": validator_party(tok),
                "expectedDso": dso_party(tok),
            },
        }
    }

    result = submit_external(tok, party, command)

    print("SUCCESS: PreApproval created")
    print_json(result)


if __name__ == "__main__":
    main()