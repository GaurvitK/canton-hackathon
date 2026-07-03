from common import *


def main():
    tok = token()

    if KEY_FILE.exists() or PARTY_FILE.exists():
        raise SystemExit(
            "Key/party already exists in .cantor8/. "
            "Delete it only if you want a fresh party."
        )

    private, public_hex = new_key()

    generated = post(
        tok,
        f"{VALIDATOR_API}/v0/admin/external-party/topology/generate",
        {
            "party_hint": PARTY_HINT,
            "public_key": public_hex,
        },
    )

    signed = [
        {
            "topology_tx": tx["topology_tx"],
            "signed_hash": sign_hex(private, tx["hash"]),
        }
        for tx in generated["topology_txs"]
    ]

    submitted = post(
        tok,
        f"{VALIDATOR_API}/v0/admin/external-party/topology/submit",
        {
            "public_key": public_hex,
            "signed_topology_txs": signed,
        },
    )

    pid = submitted.get("party_id", generated["party_id"])
    save_party_id(pid)

    print_json(
        {
            "party_id": pid,
            "public_key_hex": public_hex,
            "key_file": str(KEY_FILE),
            "party_file": str(PARTY_FILE),
        }
    )


if __name__ == "__main__":
    main()