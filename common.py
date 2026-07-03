import base64
import json
import os
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


load_dotenv()

AUTH_URL = os.getenv("AUTH_URL")
VALIDATOR_API = os.getenv("VALIDATOR_API")
LEDGER_API = os.getenv("LEDGER_API")

CLIENT_ID = os.getenv("CANTON_CLIENT_ID", "hackathon")
CLIENT_SECRET = os.getenv("CANTON_CLIENT_SECRET")
PARTY_HINT = os.getenv("PARTY_HINT", "gk-hack")

CANTON_DIR = Path(".canton")
KEY_FILE = CANTON_DIR / "party-key.json"
PARTY_FILE = CANTON_DIR / "party.json"

HOLDING_INTERFACE = (
    "#splice-api-token-holding-v1:"
    "Splice.Api.Token.HoldingV1:Holding"
)

PREAPPROVAL_TEMPLATE = (
    "#splice-wallet:"
    "Splice.Wallet.TransferPreapproval:TransferPreapprovalProposal"
)

TRANSFER_FACTORY_INTERFACE = (
    "#splice-api-token-transfer-instruction-v1:"
    "Splice.Api.Token.TransferInstructionV1:TransferFactory"
)


def die(resp, action):
    if resp.ok:
        return

    print(f"\nFAILED: {action}")
    print("STATUS:", resp.status_code)

    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)

    raise SystemExit(1)


def token():
    if not CLIENT_SECRET:
        raise SystemExit("Missing CANTON_CLIENT_SECRET in .env")

    resp = requests.post(
        AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )

    die(resp, "get token")
    return resp.json()["access_token"]


def headers(tok):
    return {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get(tok, url, params=None, auth=True):
    request_headers = headers(tok) if auth else {"Accept": "application/json"}

    resp = requests.get(
        url,
        headers=request_headers,
        params=params,
        timeout=30,
    )

    die(resp, f"GET {url}")
    return resp.json()


def post(tok, url, body):
    resp = requests.post(
        url,
        headers=headers(tok),
        json=body,
        timeout=60,
    )

    die(resp, f"POST {url}")
    return resp.json()


def jwt_sub(tok):
    payload = tok.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    return claims["sub"]


def new_key():
    CANTON_DIR.mkdir(exist_ok=True)

    private_key = Ed25519PrivateKey.generate()

    raw_private = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )

    raw_public = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )

    KEY_FILE.write_text(
        json.dumps(
            {
                "private_key_base64": base64.b64encode(raw_private).decode(),
                "public_key_hex": raw_public.hex(),
            },
            indent=2,
        )
        + "\n"
    )

    return private_key, raw_public.hex()


def load_key():
    body = json.loads(KEY_FILE.read_text())

    raw_private = base64.b64decode(body["private_key_base64"])
    private_key = Ed25519PrivateKey.from_private_bytes(raw_private)

    return private_key, body["public_key_hex"]


def sign_hex(private_key, hex_digest):
    digest = bytes.fromhex(hex_digest)
    return private_key.sign(digest).hex()


def sign_prepared_hash(private_key, prepared_hash):
    try:
        digest = base64.b64decode(prepared_hash, validate=True)
    except Exception:
        digest = bytes.fromhex(prepared_hash)

    signature = private_key.sign(digest)
    return base64.b64encode(signature).decode()


def save_party_id(party_id):
    CANTON_DIR.mkdir(exist_ok=True)

    PARTY_FILE.write_text(
        json.dumps(
            {
                "party_id": party_id,
            },
            indent=2,
        )
        + "\n"
    )


def party_id():
    return json.loads(PARTY_FILE.read_text())["party_id"]


def ledger_user_id(tok):
    return jwt_sub(tok)


def ledger_end(tok):
    body = get(tok, f"{LEDGER_API}/v2/state/ledger-end")
    return int(body["offset"])


def synchronizer_id(tok, party):
    body = get(
        tok,
        f"{LEDGER_API}/v2/state/connected-synchronizers",
        params={"party": party},
    )

    syncs = body["connectedSynchronizers"]

    for sync in syncs:
        if sync.get("permission") in (
            "PARTICIPANT_PERMISSION_CONFIRMATION",
            "PARTICIPANT_PERMISSION_SUBMISSION",
        ):
            return sync["synchronizerId"]

    return syncs[0]["synchronizerId"]


def submit_external(tok, party, command, disclosed_contracts=None):
    private_key, _ = load_key()

    prepare_body = {
        "commands": [command],
        "commandId": f"prepare-{uuid.uuid4().hex}",
        "userId": ledger_user_id(tok),
        "actAs": [party],
        "readAs": [party],
        "synchronizerId": synchronizer_id(tok, party),
        "packageIdSelectionPreference": [],
        "verboseHashing": False,
    }

    if disclosed_contracts:
        prepare_body["disclosedContracts"] = disclosed_contracts

    prepared = post(
        tok,
        f"{LEDGER_API}/v2/interactive-submission/prepare",
        prepare_body,
    )

    execute_body = {
        "preparedTransaction": prepared["preparedTransaction"],
        "partySignatures": {
            "signatures": [
                {
                    "party": party,
                    "signatures": [
                        {
                            "format": "SIGNATURE_FORMAT_RAW",
                            "signature": sign_prepared_hash(
                                private_key,
                                prepared["preparedTransactionHash"],
                            ),
                            "signedBy": party.split("::", 1)[-1],
                            "signingAlgorithmSpec": "SIGNING_ALGORITHM_SPEC_ED25519",
                        }
                    ],
                }
            ]
        },
        "submissionId": f"execute-{uuid.uuid4().hex}",
        "userId": ledger_user_id(tok),
        "hashingSchemeVersion": prepared["hashingSchemeVersion"],
        "deduplicationPeriod": {
            "Empty": {}
        },
    }

    return post(
        tok,
        f"{LEDGER_API}/v2/interactive-submission/executeAndWaitForTransaction",
        execute_body,
    )


def active_holdings(tok, party):
    body = {
        "activeAtOffset": ledger_end(tok),
        "eventFormat": {
            "filtersByParty": {
                party: {
                    "cumulative": [
                        {
                            "identifierFilter": {
                                "InterfaceFilter": {
                                    "value": {
                                        "interfaceId": HOLDING_INTERFACE,
                                        "includeInterfaceView": True,
                                        "includeCreatedEventBlob": True,
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "verbose": False,
        },
    }

    return post(
        tok,
        f"{LEDGER_API}/v2/state/active-contracts",
        body,
    )


def parse_holdings(acs):
    items = []

    for entry in acs:
        contract_entry = entry.get("contractEntry", {})
        active = (
            contract_entry.get("JsActiveContract")
            or contract_entry.get("ActiveContract")
        )

        if not active:
            continue

        created = active.get("createdEvent", {})
        views = created.get("interfaceViews", [])

        if isinstance(views, dict):
            views = list(views.values())

        payload = None

        for view in views:
            if view.get("interfaceId") == HOLDING_INTERFACE:
                payload = view.get("viewValue", {})
                break

        if payload is None and len(views) == 1:
            payload = views[0].get("viewValue", {})

        if not payload:
            continue

        items.append(
            {
                "contractId": created["contractId"],
                "payload": payload,
                "createdEventBlob": created.get("createdEventBlob"),
            }
        )

    return items


def print_json(value):
    print(json.dumps(value, indent=2, default=str))