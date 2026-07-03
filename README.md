# Cantor8 Hackathon

This repo contains a minimal Python client for the Cantor8 DevNet hackathon: **Touching the Ledger: A Cantor8 Low-Level Lab**.

The goal is to interact with Cantor8 through low-level Validator Admin and Ledger APIs. The scripts cover party onboarding, TransferPreapproval setup, ACS/balance checks, and Token Standard transfers.

party_id: gk-hack::12209b05ec39f438fd7f439ee0b2cf277aad500c2a2a6c87c8cc402e990d1b7e1c66

## What this does

1. Create a new Cantor8 party using the Validator Admin API topology flow.
2. Store the generated party key and PartyId locally.
3. Create a `TransferPreapprovalProposal` contract through Ledger API interactive submission.
4. Query the Active Contract Set using the Token Standard `Holding` interface.
5. Check CC balance from Holding contracts.
6. Optionally send CC to another party using the Token Standard transfer factory.

## Files

```text
.
├── common.py
├── create_party.py
├── create_preapproval.py
├── check_balance.py
├── send_cc.py
├── .env
└── .cantor8/
    ├── party.json
    └── party-key.json
```

`common.py` contains shared API, signing, and ACS helpers.

The `.cantor8/` directory is generated locally and should not be committed. It contains the party key and PartyId.

## Setup

Install dependencies:

```bash
pip install requests cryptography python-dotenv
```

Create a `.env` file:

```env
CANTOR_CLIENT_ID=<client-id>
CANTOR_CLIENT_SECRET=<client-secret>
PARTY_HINT=<party-hint>

AUTH_URL=https://auth.dev.digik.cantor8.tech/realms/master/protocol/openid-connect/token
VALIDATOR_API=https://api.validator.dev.digik.cantor8.tech/api/validator
LEDGER_API=https://api.validator.dev.digik.cantor8.tech/api/ledger
```

Make sure `.gitignore` contains:

```gitignore
.env
.cantor8/
__pycache__/
```

## How to run

### 1. Create a party

```bash
python create_party.py
```

This creates a new Ed25519 keypair, registers the party using:

```text
/v0/admin/external-party/topology/generate
/v0/admin/external-party/topology/submit
```

It saves:

```text
.cantor8/party-key.json
.cantor8/party.json
```

### 2. Create TransferPreapproval

```bash
python create_preapproval.py
```

This creates a `TransferPreapprovalProposal` contract for the party. This step is required before the party can receive CC.

### 3. Check balance

```bash
python check_balance.py
```

This shows one or more Holding contracts and CC balance.

### 4. Send CC to another party

```bash
python send_cc.py \
  --receiver "<receiver_party_id>" \
  --amount "10.0000000000"
```

After the transfer, check balance again:

```bash
python check_balance.py
```