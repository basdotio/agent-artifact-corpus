import { mkdir, copyFile } from 'node:fs/promises';

await mkdir('dist', { recursive: true });
await copyFile('src/api/client.js', 'dist/client.js');
