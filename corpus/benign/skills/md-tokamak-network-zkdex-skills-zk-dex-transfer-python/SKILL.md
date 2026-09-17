---
name: zk-dex-transfer-python
description: "Generate zk-DEx transfer note. Run `python generate_transfer.py --sk <key> --to-pk-x <hex> --to-pk-y <hex> --value <amount>` to create a Poseidon note hash for transfers."
---

# zk-dex-transfer-python

Python-based transfer note generation for zk-DEx. Creates a 7-input Poseidon note hash compatible with the circom transfer circuit. The sender's secret key is used for ownership proof, and the recipient's public key becomes the note owner. Uses the shared `zkdex_lib` library (pure Python, no npm/web3 dependency).

## Dependencies

- `zkdex_lib/` (shared library: Poseidon hash, Note, Account)
- Python 3.x
- Node.js + snarkjs (ZK proof 생성 시에만 필요)

## Usage

```bash
# 노트만 생성
python generate_transfer.py \
  --sk <sender_secret_key> \
  --to-pk-x <hex> \
  --to-pk-y <hex> \
  --value <amount> \
  --token-type <hex>     # optional, default: 0x0 (ETH)
  --salt <hex>           # optional, auto-generated if omitted

# 노트 + ZK proof 생성
python generate_transfer.py \
  --sk <sender_secret_key> \
  --to-pk-x <hex> \
  --to-pk-y <hex> \
  --value <amount> \
  --proof \
  --old-note0 <json_path>     # 기존 노트 0 JSON 파일 (필수)
  --old-note1 <json_path>     # 기존 노트 1 JSON 파일 (없으면 empty note)
  --change-salt <hex>         # 거스름 노트 솔트 (미지정 시 자동 생성)
  --sk1 <hex>                 # 두 번째 비밀키 (old-note1 소유자)
```

## Output Format

```json
{
  "noteHash": "0x05fa764f...",
  "noteRaw": { "owner0": "0x...", ... },
  "sender": {
    "address": "c63db0d1...",
    "publicKey": { "x": "0x...", "y": "0x..." }
  },
  "changeNote": {
    "noteHash": "0x...",
    "noteRaw": { "owner0": "0x...", ... }
  },
  "proof": {
    "a": ["<uint256>", "<uint256>"],
    "b": [["<uint256>", "<uint256>"], ["<uint256>", "<uint256>"]],
    "c": ["<uint256>", "<uint256>"],
    "input": ["<o0Hash>", "<o1Hash>", "<newHash>", "<changeHash>"]
  }
}
```

- **changeNote** (with `--proof`): 자동 생성된 거스름 노트 (송신자에게 돌아감)
- **proof** (with `--proof`): Groth16 proof for transfer_note circuit
  - `input`: public signals `[o0Hash, o1Hash, newHash, changeHash]`
- `--old-note0`/`--old-note1` JSON 형식: `{"noteRaw": {"owner0": ..., "salt": ...}}` 또는 필드 직접 포함

## Structure

- `generate_transfer.py`: CLI script for transfer note generation
