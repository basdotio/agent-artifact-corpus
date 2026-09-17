# ChunkTech Skill

Store files and browser extensions on-chain using chunked calldata transactions.

## When to Use

- User wants to store a file permanently on-chain
- User wants to distribute a Chrome/Firefox extension without app stores
- User needs censorship-resistant file hosting
- User wants cross-chain storage (cheap L2 data, durable L1 pointer)

## Key Concepts

**Chunking**: Files are split into 33.3KB pieces, each sent as a self-transfer transaction with the data in calldata.

**Inscription**: A single transaction containing a self-loading HTML page that can fetch and reassemble data from other transactions.

**Cross-chain**: Store bulk data on Base (cheap), store the "unchunker" inscription on Ethereum (durable).

## Commands

### Upload a file to Base

```typescript
import { ChunkTech } from 'chunktech';
import { createWalletClient, http } from 'viem';
import { base } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';

const account = privateKeyToAccount(`0x${process.env.PRIVATE_KEY}`);
const walletClient = createWalletClient({ account, chain: base, transport: http() });
const ct = new ChunkTech({ walletClient });

const result = await ct.upload(fileBuffer);
console.log('TX hashes:', result.txHashes);
```

### Upload a browser extension

```typescript
import { ExtensionUploader } from 'chunktech';
import { createWalletClient, http } from 'viem';
import { base, mainnet } from 'viem/chains';
import { readFileSync } from 'fs';

const uploader = new ExtensionUploader({
  keyChain: 'ethereum',
  dataChain: 'base',
  keyWalletClient: createWalletClient({ account, chain: mainnet, transport: http() }),
  dataWalletClient: createWalletClient({ account, chain: base, transport: http() }),
});

const result = await uploader.upload({
  name: 'My Extension',
  version: '1.0.0',
  developer: 'dev.eth',
  chrome: readFileSync('dist/chrome.zip'),
  firefox: readFileSync('dist/firefox.xpi'),
});

console.log('Inscription:', result.inscriptionTxHash);
```

### Download from chain

```typescript
const result = await ct.download(txHashes);
// result.data = Uint8Array of reassembled file
```

## Architecture

```
Extension Distribution:
┌────────────────┐     ┌─────────────────┐
│ Ethereum       │     │ Base            │
│                │     │                 │
│ 1 inscription  │────▶│ N data chunks   │
│ (HTML loader)  │     │ (extension zip) │
└────────────────┘     └─────────────────┘
        │
        ▼
   User views inscription
        │
        ▼
   HTML fetches chunks from Base
        │
        ▼
   Reassembles + verifies SHA256
        │
        ▼
   Download button appears
```

## Exports

```typescript
// Main classes
ChunkTech              // Single-chain upload/download
ExtensionUploader      // Browser extension distribution
CrossChainUploader     // Generic cross-chain with HTML loader

// Utilities
chunkData              // Split file into chunks
encodeChunk            // Encode chunk for calldata
decodeChunk            // Decode chunk from calldata
sendChunks             // Send chunks as transactions
assembleFromHashes     // Reassemble from tx hashes
generateExtensionLoader // Generate extension download page HTML

// Encryption (optional)
generateEncryptionKeys
encryptForRecipients
decryptForRecipient
```

## Cost Reference

| Chain | Cost per KB | 500KB file |
|-------|-------------|------------|
| Base | ~$0.001 | ~$0.50 |
| Arbitrum | ~$0.001 | ~$0.50 |
| Ethereum | ~$0.50 | ~$250 |

Recommended: Data on Base, inscription pointer on Ethereum.

## Common Patterns

### Extension with both Chrome and Firefox builds

Upload both, inscription shows download buttons for each with browser detection.

### Encrypted file sharing

Use X3DH encryption with recipient public keys. Only specified recipients can decrypt.

### Version updates

Each version is a new inscription. Use ENS or a registry contract to point to latest.

## On-Chain Viewer Pages

Create self-contained HTML pages that fetch and display any on-chain content. Good for:
- NPM packages (auditable source)
- Browser extensions (download + install instructions)
- Any file that needs public verification

### Pattern

1. **Inscribe**: Single tx with `data:application/zip;base64,<content>`
2. **Viewer HTML**: Fetches tx via RPC, decodes, verifies SHA256, shows content

### Create an On-Chain Package Viewer

```javascript
// inscribe.js - Inscribe a zip to Base
import { readFileSync } from 'fs';
import { createPublicClient, createWalletClient, http, toHex } from 'viem';
import { base } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { createHash } from 'crypto';

const zipData = readFileSync('package.zip');
const base64 = zipData.toString('base64');
const sha256 = createHash('sha256').update(zipData).digest('hex');

const dataUri = `data:application/zip;base64,${base64}`;
const calldata = toHex(new TextEncoder().encode(dataUri));

const hash = await walletClient.sendTransaction({
  to: account.address,  // self-transfer
  data: calldata,
});
// Save hash and sha256 for viewer
```

### Viewer HTML Structure

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
</head>
<body>
  <button id="download-btn" disabled>Download</button>
  <div id="file-tabs"></div>
  <pre id="code-content"></pre>

  <script>
    const TX_HASH = '0x...';
    const EXPECTED_SHA256 = '...';
    const RPC_URL = 'https://mainnet.base.org';

    async function fetchFromChain() {
      // 1. Fetch tx via RPC
      const response = await fetch(RPC_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'eth_getTransactionByHash',
          params: [TX_HASH],
          id: 1
        })
      });
      const { result: tx } = await response.json();

      // 2. Decode calldata -> data URI -> base64 -> bytes
      const hex = tx.input.slice(2);
      const bytes = new Uint8Array(hex.length / 2);
      for (let i = 0; i < hex.length; i += 2) {
        bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
      }
      const dataUri = new TextDecoder().decode(bytes);
      const base64 = dataUri.match(/base64,(.+)$/)[1];
      const zipBytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));

      // 3. Verify SHA256
      const hashBuffer = await crypto.subtle.digest('SHA-256', zipBytes);
      const sha256 = Array.from(new Uint8Array(hashBuffer))
        .map(b => b.toString(16).padStart(2, '0')).join('');
      if (sha256 !== EXPECTED_SHA256) throw new Error('SHA256 mismatch');

      // 4. Extract and display files
      const zip = await JSZip.loadAsync(zipBytes);
      // ... build tabs, show content
    }
  </script>
</body>
</html>
```

### Viewer Features

- **Source tabs**: Show README, source files, package.json
- **Download button**: Extract verified zip from chain
- **SHA256 verification**: Proves content matches inscription
- **Install instructions**: npm install from downloaded file
- **Verify link**: Direct link to BaseScan/Etherscan tx

### Styling Presets

```css
/* Dark + Accent (e.g., black + #c3ff00) */
body { background: #000; color: #e0e0e0; }
.highlight { color: #c3ff00; }
.btn { background: #c3ff00; color: #000; }

/* Dark + Red (e.g., #0a0a0f + #e94560) */
body { background: #0a0a0f; color: #e0e0e0; }
.highlight { color: #e94560; }
.btn { background: linear-gradient(135deg, #e94560, #ff6b35); }
```

## Limitations

- Max chunk size: 33.3KB (could be larger, conservative choice)
- Chrome extensions require developer mode to install
- Firefox shows warning prompt for sideloaded extensions
- No built-in versioning (handle externally)
- Single-tx limit: ~100KB for viewers (use chunking for larger)
