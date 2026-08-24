"""Intended-path solver: CBC padding oracle attack, stdlib crypto math only."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["strip-the-padding"]
    client = httpx.Client(base_url=ctx.url(), timeout=30)
    msg = client.get("/api/message").json()
    iv = bytes.fromhex(msg["iv_hex"])
    ct = bytes.fromhex(msg["ct_hex"])
    blocks = [ct[i : i + 16] for i in range(0, len(ct), 16)]
    queries = 0

    def oracle(payload: bytes) -> bool:
        nonlocal queries
        queries += 1
        resp = client.post("/api/decrypt", json={"ct": payload.hex()})
        return bool(resp.json()["valid_padding"])

    assert oracle(ct), "original envelope must validate"

    def crack_block(prev_block: bytes, target: bytes) -> bytes:
        """Byte-at-a-time recovery of AES_decrypt(target) xor prev_block."""
        intermediate = bytearray(16)
        plain = bytearray(16)
        for pad_byte in range(1, 17):
            forged = bytearray(16)
            for known in range(16 - pad_byte + 1, 16):
                forged[known] = intermediate[known] ^ pad_byte
            pos = 16 - pad_byte
            found = None
            for guess in range(256):
                forged[pos] = guess
                if not oracle(bytes(forged) + target):
                    continue
                if pad_byte == 16:
                    found = guess
                    break
                # Disambiguate: a genuine pad_byte-length pad ignores the
                # byte before it; an accidental longer pad does not.
                forged[pos - 1] ^= 0xFF
                genuine = oracle(bytes(forged) + target)
                forged[pos - 1] ^= 0xFF
                if genuine:
                    found = guess
                    break
            assert found is not None, f"oracle gave no candidate at pad_byte={pad_byte}"
            intermediate[pos] = found ^ pad_byte
            plain[pos] = intermediate[pos] ^ prev_block[pos]
        return bytes(plain)

    recovered = bytearray()
    # Data block 1 chains against ciphertext block 0 (the banner block);
    # the IV would only matter for attacking block 0 itself.
    previous = blocks[0]
    for index in range(1, len(blocks)):
        recovered.extend(crack_block(previous, blocks[index]))
        previous = blocks[index]
    client.close()

    plaintext = bytes(recovered)
    pad_len = plaintext[-1]
    assert 1 <= pad_len <= 16 and plaintext.endswith(bytes([pad_len]) * pad_len)
    stripped = plaintext[:-pad_len]

    flags = find_flags(stripped.decode("ascii", "replace"))
    captured = flags[0] if flags else None
    ok = captured == expected and queries > 50
    detail = None if ok else f"plain={stripped!r} queries={queries}"
    return SolveResult(
        results=[TaskResult(task_id="strip-the-padding", ok=ok, captured=captured, detail=detail)]
    )
