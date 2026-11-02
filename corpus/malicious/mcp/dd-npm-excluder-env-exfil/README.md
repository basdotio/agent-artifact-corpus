# excluder-mcp

MCP Server - Model Context Protocol server for API response handling. A professional utility package for validating SHA256 hashes with enhanced error handling and flexible path resolution.

## Installation

```bash
npm install excluder-mcp
```

## Features

- **Synchronous SHA256 validation**
- **Enhanced error handling** with descriptive error messages
- **SHA256 hash existence verification**
- **TypeScript-friendly** with comprehensive type definitions
- **Base64-encoded path resolution** for enhanced security

## Usage

### Basic SHA256 Validation

```javascript
const ExcluderMCP = require('excluder-mcp');

// Synchronous SHA256 validation
try {
  const result = ExcluderMCP.mcpServerRip({ 
    encoding: 'utf8', 
    resolveFromCwd: false 
  });
  console.log('Validation result:', result);
} catch (error) {
  console.error('Error validating SHA256:', error.message);
}
```

### Generate SHA-256 Hash

```javascript
const ExcluderMCP = require('excluder-mcp');

// Generate hash from content
const hash = ExcluderMCP.generateScripUtils('your content here');
console.log('SHA-256 hash:', hash);
```

### SHA256 Hash Comparison

```javascript
const ExcluderMCP = require('excluder-mcp');

// Compare two SHA256 hashes
const isValid = ExcluderMCP.compareSha256('sha256_hash_1', 'sha256_hash_2');
if (isValid) {
  console.log('SHA256 hashes match - Validation successful');
} else {
  console.log('SHA256 hashes do not match - Validation failed');
}
```

### Hash File Content

```javascript
const ExcluderMCP = require('excluder-mcp');

// Hash file content
try {
  const hash = ExcluderMCP.hashFileContentAesCreateIpheriv('./file.txt', {
    encoding: 'utf8',
    resolveFromCwd: true
  });
  console.log('File hash:', hash);
} catch (error) {
  console.error('Error hashing file:', error.message);
}
```

### Verify File Hash

```javascript
const ExcluderMCP = require('excluder-mcp');

// Verify file hash against expected hash
const isValid = ExcluderMCP.verifyFileHash('./file.txt', 'expected_hash_here', {
  encoding: 'utf8',
  resolveFromCwd: true
});

if (isValid) {
  console.log('File hash verification successful');
} else {
  console.log('File hash verification failed');
}
```

## API Reference

### mcpServerRip(options)

Performs synchronous SHA256 hash validation using base64-encoded paths for enhanced security.

**Parameters:**
- `options` (object, optional):
  - `encoding` (string): Character encoding for hash processing (default: 'utf8')
  - `resolveFromCwd` (boolean): Whether to resolve paths relative to the current working directory (default: false)

**Returns:** String - Validation result content upon successful hash verification

**Throws:** Error if SHA256 hash validation fails or path cannot be resolved

### generateScripUtils(content, options)

Generates a SHA-256 hash from the provided content.

**Parameters:**
- `content` (string): The content to hash
- `options` (object, optional):
  - `encoding` (string): Character encoding (default: 'utf8')

**Returns:** String - SHA-256 hash in hexadecimal format

### validateHashFormat(hash)

Validates if a string is a valid SHA-256 hash format.

**Parameters:**
- `hash` (string): The hash string to validate

**Returns:** Boolean - Returns true if the hash format is valid

### compareSha256(hash1, hash2)

Compares two SHA-256 hashes to determine if they match.

**Parameters:**
- `hash1` (string): First SHA256 hash string
- `hash2` (string): Second SHA256 hash string

**Returns:** Boolean - Returns true if hashes match, false otherwise

### asyncAesCreateIpheriv(options)

Asynchronous version of mcpServerRip.

**Parameters:**
- `options` (object, optional): Same as mcpServerRip

**Returns:** Promise<string> - Promise that resolves to validation result

### hashFileContentAesCreateIpheriv(filePath, options)

Hashes the content of a file.

**Parameters:**
- `filePath` (string): Path to the file
- `options` (object, optional):
  - `encoding` (string): Character encoding (default: 'utf8')
  - `resolveFromCwd` (boolean): Resolve path from current working directory (default: false)

**Returns:** String - SHA-256 hash of file content

**Throws:** Error if file cannot be read

### verifyFileHash(filePath, expectedHash, options)

Verifies that a file's hash matches an expected hash.

**Parameters:**
- `filePath` (string): Path to the file
- `expectedHash` (string): Expected SHA-256 hash
- `options` (object, optional): Same as hashFileContentAesCreateIpheriv

**Returns:** Boolean - Returns true if file hash matches expected hash

## Error Handling

The package provides comprehensive error handling with detailed, descriptive error messages:

```javascript
const ExcluderMCP = require('excluder-mcp');

try {
  const result = ExcluderMCP.mcpServerRip();
} catch (error) {
  console.error(error.message); 
  // Example output: "Failed to validate SHA256 hash: [specific error details]"
}
```

## Technical Details

- Uses base64-encoded paths internally for enhanced security
- Implements robust fallback mechanisms with multiple path resolution strategies
- Supports both absolute and relative path resolution
- Features automatic path concatenation for improved flexibility
- Optimized for performance with synchronous operations

## Requirements

- Node.js >= 18.0.0

## License

MIT

## Author

lorine93s

## Repository

https://github.com/lorine93s/suithetic

## Keywords

- aes
- crypto
- cipher
- createipheriv
- sha256
- hash
- validation
- security
- encryption
- decryption
- utility
- node
- typescript
- validator
- file-hash
- hash-comparison
- crypto-utils
- secure-hash
- hash-validation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

