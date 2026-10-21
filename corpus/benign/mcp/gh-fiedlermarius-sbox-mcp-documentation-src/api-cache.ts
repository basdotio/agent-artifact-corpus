import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

// ----- Shared type definitions (mirrors Facepunch.AssemblySchema JSON schema) -----

export interface ApiDocumentation {
    Summary?: string;
    Remarks?: string;
    Return?: string;
    Params?: Record<string, string>;
    Exceptions?: Record<string, string>;
    TypeParams?: Record<string, string>;
    SeeAlso?: string[];
    Examples?: string[];
}

export interface ApiParameter {
    Name: string;
    /** JsonPropertyName("Out") */
    Out?: boolean;
    /** JsonPropertyName("In") */
    In?: boolean;
    Type?: string;
}

export interface ApiMethod {
    FullName: string;
    Name: string;
    IsPublic: boolean;
    IsProtected?: boolean;
    IsStatic?: boolean;
    IsExtension?: boolean;
    ReturnType?: string;
    IsVirtual?: boolean;
    IsOverride?: boolean;
    Parameters?: ApiParameter[];
    Documentation?: ApiDocumentation;
}

export interface ApiProperty {
    FullName: string;
    Name: string;
    IsPublic: boolean;
    IsProtected?: boolean;
    IsStatic?: boolean;
    PropertyType?: string;
    Documentation?: ApiDocumentation;
}

export interface ApiField {
    FullName: string;
    Name: string;
    IsPublic: boolean;
    IsProtected?: boolean;
    IsStatic?: boolean;
    FieldType?: string;
    Documentation?: ApiDocumentation;
}

export interface ApiType {
    FullName: string;
    Name: string;
    Namespace?: string;
    BaseType?: string;
    IsPublic: boolean;
    IsProtected?: boolean;
    IsStatic?: boolean;
    IsClass?: boolean;
    IsInterface?: boolean;
    IsAbstract?: boolean;
    IsSealed?: boolean;
    IsAttribute?: boolean;
    Methods?: ApiMethod[];
    Constructors?: ApiMethod[];
    Properties?: ApiProperty[];
    Fields?: ApiField[];
    Documentation?: ApiDocumentation;
}

// ----- Cache -----

interface ApiCacheManifest {
    version: number;
    schemaUrl: string;
    fetchedAt: number;
    typeCount: number;
}

const CACHE_VERSION = 1;
const DEFAULT_TTL_SECONDS = 86400; // 24 hours — schema changes with each build

export class ApiCache {
    private cacheDir: string;
    private manifestPath: string;
    private typesPath: string;
    private ttlMs: number;
    private manifest: ApiCacheManifest;

    constructor() {
        const base =
            process.env["SBOX_DOCS_CACHE_DIR"] ||
            path.join(os.homedir(), ".sbox-docs-mcp", "cache");
        this.cacheDir = base;
        this.manifestPath = path.join(base, "api-manifest.json");
        this.typesPath = path.join(base, "api-types.json");
        this.ttlMs =
            parseInt(process.env["SBOX_API_CACHE_TTL"] || String(DEFAULT_TTL_SECONDS), 10) *
            1000;
        this.manifest = { version: CACHE_VERSION, schemaUrl: "", fetchedAt: 0, typeCount: 0 };
    }

    async init(): Promise<void> {
        fs.mkdirSync(this.cacheDir, { recursive: true });
        if (fs.existsSync(this.manifestPath)) {
            try {
                const raw = fs.readFileSync(this.manifestPath, "utf-8");
                const parsed = JSON.parse(raw) as ApiCacheManifest;
                if (parsed.version === CACHE_VERSION) {
                    this.manifest = parsed;
                }
            } catch {
                // Corrupt cache — start fresh
            }
        }
    }

    isFresh(): boolean {
        if (this.manifest.fetchedAt === 0) return false;
        return Date.now() - this.manifest.fetchedAt < this.ttlMs;
    }

    getTypeCount(): number {
        return this.manifest.typeCount;
    }

    getSchemaUrl(): string {
        return this.manifest.schemaUrl;
    }

    loadTypes(): ApiType[] | null {
        if (!fs.existsSync(this.typesPath)) return null;
        try {
            const raw = fs.readFileSync(this.typesPath, "utf-8");
            return JSON.parse(raw) as ApiType[];
        } catch {
            return null;
        }
    }

    save(schemaUrl: string, types: ApiType[]): void {
        fs.mkdirSync(this.cacheDir, { recursive: true });
        fs.writeFileSync(this.typesPath, JSON.stringify(types), "utf-8");
        this.manifest = {
            version: CACHE_VERSION,
            schemaUrl,
            fetchedAt: Date.now(),
            typeCount: types.length,
        };
        fs.writeFileSync(this.manifestPath, JSON.stringify(this.manifest), "utf-8");
    }

    clear(): void {
        this.manifest = { version: CACHE_VERSION, schemaUrl: "", fetchedAt: 0, typeCount: 0 };
        if (fs.existsSync(this.typesPath)) fs.unlinkSync(this.typesPath);
        if (fs.existsSync(this.manifestPath))
            fs.writeFileSync(this.manifestPath, JSON.stringify(this.manifest), "utf-8");
    }

    // --- Self-Test ---
    static runSelfTest(): { passed: string[]; failed: string[] } {
        const passed: string[] = [];
        const failed: string[] = [];

        function assert(name: string, condition: boolean) {
            (condition ? passed : failed).push(name);
        }

        const tmpDir = path.join(os.tmpdir(), `sbox-api-cache-test-${Date.now()}`);
        process.env["SBOX_DOCS_CACHE_DIR"] = tmpDir;

        try {
            const cache = new ApiCache();

            assert("new cache is not fresh", !cache.isFresh());
            assert("new cache typeCount is 0", cache.getTypeCount() === 0);
            assert("loadTypes on empty returns null", cache.loadTypes() === null);

            const fakeTypes: ApiType[] = [
                {
                    FullName: "Sandbox.Component",
                    Name: "Component",
                    Namespace: "Sandbox",
                    IsPublic: true,
                    IsClass: true,
                    Documentation: { Summary: "Base component class." },
                },
            ];

            cache.save("https://cdn.sbox.game/releases/test.zip.json", fakeTypes);

            assert("cache is fresh after save", cache.isFresh());
            assert("typeCount is 1 after save", cache.getTypeCount() === 1);

            const loaded = cache.loadTypes();
            assert("loadTypes returns array", Array.isArray(loaded));
            assert("loaded type has correct name", loaded?.[0]?.Name === "Component");

            cache.clear();
            assert("cache not fresh after clear", !cache.isFresh());
        } finally {
            process.env["SBOX_DOCS_CACHE_DIR"] = undefined as unknown as string;
            try {
                fs.rmSync(tmpDir, { recursive: true, force: true });
            } catch {
                // cleanup best-effort
            }
        }

        return { passed, failed };
    }
}
