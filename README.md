# Canton Hackathon

This repo contains a minimal Python client for the Canton DevNet hackathon: **Touching the Ledger: A Canton Low-Level Lab**.

The goal is to interact with Canton through low-level Validator Admin and Ledger APIs. The scripts cover party onboarding, TransferPreapproval setup, ACS/balance checks, and Token Standard transfers.

## What this does

1. Create a new Canton party using the Validator Admin API topology flow.
2. Store the generated party key and PartyId locally.
3. Create a `TransferPreapprovalProposal` contract through Ledger API interactive submission.
4. Query the Active Contract Set using the Token Standard `Holding` interface.
5. Check CC balance from Holding contracts.
6. Optionally send CC to another party using the Token Standard transfer factory.

## Files

```text
.
├── common.py
├── 01_create_party.py
├── 02_create_preapproval.py
├── 03_check_balance.py
├── 04_send_cc.py
├── .env
└── .canton/
    ├── party.json
    └── party-key.json
```

`common.py` contains shared API, signing, and ACS helpers.

The `.canton/` directory is generated locally and should not be committed. It contains the party key and PartyId.

## Setup

Install dependencies:

```bash
pip install requests cryptography python-dotenv
```

Create a `.env` file:

```env
CANTON_CLIENT_ID=<client-id>
CANTON_CLIENT_SECRET=<client-secret>
PARTY_HINT=<party-hint>

AUTH_URL=https://auth.dev.digik.cantor8.tech/realms/master/protocol/openid-connect/token
VALIDATOR_API=https://api.validator.dev.digik.cantor8.tech/api/validator
LEDGER_API=https://api.validator.dev.digik.cantor8.tech/api/ledger
```

Make sure `.gitignore` contains:

```gitignore
.env
.canton/
__pycache__/
```

## How to run

### 1. Create a party

```bash
python 01_create_party.py
```

This creates a new Ed25519 keypair, registers the party using:

```text
/v0/admin/external-party/topology/generate
/v0/admin/external-party/topology/submit
```

It saves:

```text
.canton/party-key.json
.canton/party.json
```

### 2. Create TransferPreapproval

```bash
python 02_create_preapproval.py
```

This creates a `TransferPreapprovalProposal` contract for the party. This step is required before the party can receive CC.

### 3. Check balance

```bash
python 03_check_balance.py
```

This shows one or more Holding contracts and CC balance.

### 4. Send CC to another party

```bash
python 04_send_cc.py \
  --receiver "<receiver_party_id>" \
  --amount "10.0000000000"
```

After the transfer, check balance again:

```bash
python 03_check_balance.py
```