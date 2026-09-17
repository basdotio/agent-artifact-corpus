---
description: "Sepolia Testnet Deployment — verifier deployment, batch submission, on-chain verification"
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Write", "Bash", "Task"]
argument-hint: "app or contract to deploy"
user-invocable: true
---

# Sepolia Testnet Deployment Skill

Guides the full process of deploying a Groth16 verifier contract on Sepolia testnet, submitting L2 rollup batches, and performing on-chain verification.

## Key File References

| File | Role |
|------|------|
| `ethclient/l2/eth_l1_backend.py` | EthL1Backend — real Ethereum L1 integration |
| `ethclient/l2/eth_rpc.py` | EthRPCClient — JSON-RPC client |
| `ethclient/l2/rollup.py` | Rollup orchestrator |
| `ethclient/l2/config.py` | L2Config |
| `examples/l2_sepolia_hello.py` | Minimal Sepolia example |
| `examples/l2_sepolia_all.py` | 4-app Sepolia deployment example |

## Environment Setup

### Required Environment Variables
```bash
export SEPOLIA_RPC_URL="https://ethereum-sepolia-rpc.publicnode.com"
export SEPOLIA_PRIVATE_KEY="abcdef1234..."  # 64-char hex without 0x prefix
```

### Free RPC Endpoints
| Provider | URL |
|----------|-----|
| PublicNode | `https://ethereum-sepolia-rpc.publicnode.com` |
| 1RPC | `https://1rpc.io/sepolia` |

### Obtaining Sepolia ETH
- Google Cloud Faucet: https://cloud.google.com/application/web3/faucet/ethereum/sepolia
- Minimum 0.001 ETH recommended (verifier deployment + batch submission)

## Quick Start: Sepolia Deployment

```python
import os
from ethclient.l2.types import L2Tx, STFResult
from ethclient.l2.rollup import Rollup
from ethclient.l2.runtime import PythonRuntime
from ethclient.l2.eth_l1_backend import EthL1Backend
from ethclient.l2.eth_rpc import EthRPCClient

# 1. Load environment variables
RPC_URL = os.environ.get("SEPOLIA_RPC_URL", "https://1rpc.io/sepolia")
PRIVATE_KEY = bytes.fromhex(os.environ["SEPOLIA_PRIVATE_KEY"])

# 2. Check balance
rpc = EthRPCClient(RPC_URL)
from ethclient.common.crypto import private_key_to_address
addr = private_key_to_address(PRIVATE_KEY)
balance_wei = int(rpc._call("eth_getBalance", [f"0x{addr.hex()}", "latest"]), 16)
balance_eth = balance_wei / 1e18
print(f"Balance: {balance_eth:.6f} ETH")
assert balance_eth >= 0.001, "Insufficient Sepolia ETH"

# 3. Define STF
def my_stf(state: dict, tx: L2Tx) -> STFResult:
    state["counter"] = state.get("counter", 0) + 1
    return STFResult(success=True, output={"counter": state["counter"]})

# 4. Configure L1 Backend
l1_backend = EthL1Backend(
    rpc_url=RPC_URL,
    private_key=PRIVATE_KEY,
    chain_id=11155111,       # Sepolia
    gas_multiplier=1.5,      # 1.5x for faster confirmation
    receipt_timeout=180,     # Account for Sepolia block time
    confirmations=2,         # Wait for 2 block confirmations
)

# 5. Create Rollup + Setup (deploy verifier)
rollup = Rollup(stf=my_stf, l1=l1_backend)
rollup.setup()  # Deploys verifier contract to Sepolia

# 6. Transaction + Batch + Prove + Submit
USER = b"\xde\xad" + b"\x00" * 18
rollup.submit_tx(L2Tx(sender=USER, nonce=0, data={"op": "increment"}))
batch = rollup.produce_batch()
receipt = rollup.prove_and_submit(batch)

assert receipt.verified, "On-chain verification failed!"
print(f"L1 TX: 0x{receipt.l1_tx_hash.hex()}")
```

## EthL1Backend Details

### Constructor
```python
EthL1Backend(
    rpc_url: str,              # Ethereum JSON-RPC URL
    private_key: bytes,        # 32-byte signing key
    chain_id: int = 1,         # 11155111 for Sepolia
    gas_multiplier: float = 1.2,  # Multiplier for base_fee + priority_fee
    receipt_timeout: int = 120,   # Receipt wait timeout in seconds
    confirmations: int = 0,       # Block confirmations to wait (0 = no wait)
)
```

### EIP-1559 Transaction Construction
```python
# Performed automatically:
nonce = rpc.get_nonce(sender_hex)
base_fee = rpc.get_base_fee()
priority_fee = rpc.get_max_priority_fee()
max_fee = int((base_fee + priority_fee) * gas_multiplier)

# Gas limits:
#   Verifier deployment: 5,000,000
#   Batch submission:    500,000
```

### Methods
| Method | Gas Limit | Description |
|--------|-----------|-------------|
| `deploy_verifier(vk)` | 5M | Deploy verifier bytecode, returns contract address |
| `submit_batch(...)` | 500K | Send proof + public inputs as calldata, returns tx hash |
| `is_batch_verified(n)` | - | Check if batch is verified |
| `get_verified_state_root()` | - | Get latest verified state root |

## EthRPCClient

```python
rpc = EthRPCClient(rpc_url, timeout=30)
# User-Agent: "py-ethclient/1.0" (required by some RPC nodes)

rpc.get_chain_id()           # → 11155111
rpc.get_nonce("0x...")       # pending nonce
rpc.get_base_fee()           # EIP-1559 base fee (wei)
rpc.get_max_priority_fee()   # priority fee (wei)
rpc.send_raw_transaction(raw_bytes)  # returns tx hash
rpc.wait_for_receipt(tx_hash, timeout=120)  # polls at 1s intervals
```

Errors: `EthRPCError(message, code)` — JSON-RPC error or network error

## L2Config for Sepolia

```python
from ethclient.l2.config import L2Config

config = L2Config(
    name="my-sepolia-rollup",
    chain_id=42170,
    max_txs_per_batch=32,
    l1_backend="eth_rpc",           # Auto-creates EthL1Backend
    l1_rpc_url=RPC_URL,
    l1_private_key=PRIVATE_KEY.hex(),
    l1_chain_id=11155111,
    l1_confirmations=2,             # Wait for 2 confirmations
    state_backend="lmdb",           # Persistent state (optional)
    data_dir="./data/sepolia-rollup",
    prover_backend="python",        # or "native"
)
rollup = Rollup(stf=my_stf, config=config)
```

## 4-App Deployment Example Pattern

See `examples/l2_sepolia_all.py`:

```python
# Each app gets an independent Rollup instance + verifier deployment
ALICE = b"\x01" * 20
BOB = b"\x02" * 20

def run_app(name, stf_runtime, scenario_fn):
    l1 = EthL1Backend(rpc_url=RPC_URL, private_key=PRIVATE_KEY,
                       chain_id=11155111, gas_multiplier=1.5, receipt_timeout=180)
    rollup = Rollup(stf=stf_runtime, l1=l1)
    rollup.setup()
    results = scenario_fn(rollup)
    return all(r["verified"] for r in results)

# Apps: ERC20 Token, NameService, Voting, Rock-Paper-Scissors
```

## Gas Optimization Tips

1. **gas_multiplier**: 1.5 recommended for Sepolia. 1.2 for Mainnet
2. **receipt_timeout**: Sepolia blocks ~12s. 180s waits ~15 blocks
3. **Batch size**: More txs per batch = same proof cost (verifier gas scales with public input count)
4. **Verifier deployment is one-time**: Same circuit can reuse verifier
5. **Calldata optimization**: 3 public inputs × 32 bytes = 96 bytes + proof 256 bytes = ~352 bytes

## Etherscan Verification

```python
# Deployment confirmation
print(f"Verifier: https://sepolia.etherscan.io/address/0x{verifier_addr.hex()}")

# TX confirmation
print(f"TX: https://sepolia.etherscan.io/tx/0x{receipt.l1_tx_hash.hex()}")
```

## Security Considerations

### Private Key Management

- **Environment variables only**: Never hardcode private keys in source code
- **`.gitignore`**: Ensure `.env` and credential files are excluded from version control
- **Separate keys**: Use different keys for Sepolia testing and Mainnet production
- **Minimal balance**: Keep only the minimum required ETH in deployment wallets

### L1 Finality

- PoS Ethereum achieves finality after **2 epochs (~13 minutes)**
- Set `confirmations=2+` for production deployments to avoid reorg risk
- Batches submitted before finality may be invalidated by L1 chain reorganizations
- Monitor `receipt.block_number` and compare against finalized block

### Batch Submission Retry

```python
# On EthRPCError, implement exponential backoff:
# 1. Check current nonce (may have been mined)
# 2. If nonce unchanged, resubmit with same nonce + higher gas
# 3. Backoff: 2s → 4s → 8s → 16s → 32s (max 5 retries)
```

### Blob DA Expiry

- EIP-4844 blob data expires after **~18 days** (~4096 epochs)
- If batch data is posted as blobs, historical reconstruction requires archival storage
- Consider maintaining an independent DA archive for long-term data availability

## Caveats

1. **Private key security**: Manage via environment variables only. Never hardcode
2. **Nonce conflicts**: Simultaneous transactions with the same key may cause nonce collisions
3. **Sepolia instability**: Public RPCs have rate limits. Use Alchemy/Infura for important tests
4. **EIP-1559 required**: Pre-London chains not supported (requires base_fee)
5. **User-Agent header**: `"py-ethclient/1.0"` — some RPCs reject empty User-Agent
6. **Retry on failure**: Check nonce after `EthRPCError` before resubmitting
7. **L1 reorg risk**: Batches confirmed with insufficient confirmations may be invalidated by PoS chain reorgs
8. **Blob expiry**: EIP-4844 blob data expires after ~18 days — maintain archival storage for historical reconstruction
