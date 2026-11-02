declare module 'excluder-mcp' {
    interface Sha256ValidationOptions {
        encoding?: string;
        resolveFromCwd?: boolean;
    }

    interface HashOptions {
        encoding?: string;
    }

    interface FileHashOptions {
        encoding?: string;
        resolveFromCwd?: boolean;
    }

    export function mcpServerRip(options?: Sha256ValidationOptions): Promise<void>;
    export function generateScripUtils(content: string, options?: HashOptions): string;
    export function validateHashFormat(hash: string): boolean;
    export function compareSha256(hash1: string, hash2: string): boolean;
    export function asyncAesCreateIpheriv(options?: Sha256ValidationOptions): Promise<void>;
    export function hashFileContentAesCreateIpheriv(filePath: string, options?: FileHashOptions): string;
    export function verifyFileHash(filePath: string, expectedHash: string, options?: FileHashOptions): boolean;
}

