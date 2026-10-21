import MiniSearch from "minisearch";
import type { ApiType } from "./api-cache.js";

export interface ApiSearchResult {
    fullName: string;
    name: string;
    namespace: string;
    description: string;
    url: string;
    topMembers: string[];
    score: number;
}

function typeUrl(type: ApiType): string {
    return `https://sbox.game/api/t/${type.FullName}`;
}

function collectMemberNames(type: ApiType): string[] {
    const names: string[] = [];
    for (const m of type.Methods ?? []) names.push(m.Name);
    for (const p of type.Properties ?? []) names.push(p.Name);
    for (const f of type.Fields ?? []) names.push(f.Name);
    return names;
}

function formatMethodSignature(m: { Name: string; ReturnType?: string; Parameters?: Array<{ Name: string; Type?: string; Out?: boolean }> }): string {
    const params = (m.Parameters ?? [])
        .map((p) => {
            const prefix = p.Out ? "out " : "";
            return p.Type ? `${prefix}${p.Type} ${p.Name}` : `${prefix}${p.Name}`;
        })
        .join(", ");
    const ret = m.ReturnType && m.ReturnType !== "void" ? m.ReturnType : "void";
    return `${ret} ${m.Name}(${params})`;
}

export function formatTypeDetail(type: ApiType, startIndex: number, maxLength: number): string {
    const lines: string[] = [];

    // Header
    const kind = type.IsInterface ? "interface" : type.IsAbstract ? "abstract class" : "class";
    lines.push(`# ${type.FullName}`);
    lines.push(`**Type:** ${kind} | **Namespace:** ${type.Namespace ?? "(global)"}`);
    if (type.BaseType) lines.push(`**Inherits:** ${type.BaseType}`);
    lines.push(`**URL:** [${typeUrl(type)}](${typeUrl(type)})`);
    lines.push("");

    const summary = type.Documentation?.Summary;
    if (summary) {
        lines.push(summary);
        lines.push("");
    }

    if (type.Constructors && type.Constructors.length > 0) {
        lines.push("## Constructors");
        for (const c of type.Constructors) {
            const sig = formatMethodSignature(c);
            lines.push(`- \`${sig}\``);
            if (c.Documentation?.Summary) lines.push(`  ${c.Documentation.Summary}`);
        }
        lines.push("");
    }

    if (type.Properties && type.Properties.length > 0) {
        lines.push("## Properties");
        for (const p of type.Properties) {
            const stat = p.IsStatic ? "static " : "";
            lines.push(`- \`${stat}${p.PropertyType ?? "?"} ${p.Name}\``);
            if (p.Documentation?.Summary) lines.push(`  ${p.Documentation.Summary}`);
        }
        lines.push("");
    }

    if (type.Methods && type.Methods.length > 0) {
        lines.push("## Methods");
        for (const m of type.Methods) {
            const stat = m.IsStatic ? "static " : "";
            const sig = formatMethodSignature(m);
            lines.push(`- \`${stat}${sig}\``);
            if (m.Documentation?.Summary) lines.push(`  ${m.Documentation.Summary}`);
        }
        lines.push("");
    }

    if (type.Fields && type.Fields.length > 0) {
        lines.push("## Fields");
        for (const f of type.Fields) {
            const stat = f.IsStatic ? "static " : "";
            lines.push(`- \`${stat}${f.FieldType ?? "?"} ${f.Name}\``);
            if (f.Documentation?.Summary) lines.push(`  ${f.Documentation.Summary}`);
        }
        lines.push("");
    }

    const full = lines.join("\n");
    const totalLength = full.length;
    const start = Math.min(startIndex, totalLength);
    const chunk = full.slice(start, start + maxLength);
    const endIndex = start + chunk.length;
    const hasMore = endIndex < totalLength;

    const footer = hasMore
        ? `\n\n---\n_Showing characters ${start}–${endIndex} of ${totalLength}. Use start_index=${endIndex} to read the next chunk._`
        : `\n\n---\n_End of type page (${totalLength} characters total)._`;

    return chunk + footer;
}

export class ApiSearch {
    private index: MiniSearch;
    private types: Map<string, ApiType> = new Map();

    constructor() {
        this.index = new MiniSearch({
            fields: ["name", "fullName", "namespace", "description", "memberNames"],
            storeFields: ["fullName"],
            searchOptions: {
                boost: { name: 4, fullName: 3, namespace: 1.5, memberNames: 2, description: 1 },
                fuzzy: 0.2,
                prefix: true,
            },
        });
    }

    buildIndex(types: ApiType[]): void {
        this.types.clear();
        this.index.removeAll();

        const docs = types.map((t, i) => ({
            id: i,
            fullName: t.FullName,
            name: t.Name,
            namespace: t.Namespace ?? "",
            description: t.Documentation?.Summary ?? "",
            memberNames: collectMemberNames(t).join(" "),
        }));

        this.index.addAll(docs);
        for (const t of types) {
            this.types.set(t.FullName, t);
            // Also index by short name for easier lookup
            if (!this.types.has(t.Name)) {
                this.types.set(t.Name, t);
            }
        }
    }

    search(query: string, limit: number = 8): ApiSearchResult[] {
        const results = this.index.search(query);
        return results.slice(0, limit).map((r) => {
            const fullName = (r as unknown as { fullName: string }).fullName ?? "";
            const type = this.types.get(fullName);
            return {
                fullName,
                name: type?.Name ?? fullName,
                namespace: type?.Namespace ?? "",
                description: type?.Documentation?.Summary ?? "",
                url: type ? typeUrl(type) : `https://sbox.game/api/t/${fullName}`,
                topMembers: type ? collectMemberNames(type).slice(0, 5) : [],
                score: r.score,
            };
        });
    }

    getType(name: string): ApiType | undefined {
        return this.types.get(name);
    }

    get typeCount(): number {
        // Map has both FullName and Name keys — count unique FullNames
        const seen = new Set<string>();
        for (const t of this.types.values()) seen.add(t.FullName);
        return seen.size;
    }

    // --- Self-Test ---
    static runSelfTest(): { passed: string[]; failed: string[] } {
        const passed: string[] = [];
        const failed: string[] = [];

        function assert(name: string, condition: boolean) {
            (condition ? passed : failed).push(name);
        }

        const search = new ApiSearch();

        assert("empty index has 0 types", search.typeCount === 0);
        assert("search on empty returns []", search.search("anything").length === 0);

        const testTypes: ApiType[] = [
            {
                FullName: "Sandbox.Component",
                Name: "Component",
                Namespace: "Sandbox",
                IsPublic: true,
                IsClass: true,
                Documentation: { Summary: "Base class for all components." },
                Methods: [
                    { FullName: "Sandbox.Component.OnStart", Name: "OnStart", IsPublic: true, IsProtected: false, IsStatic: false, IsExtension: false, ReturnType: "void", Parameters: [] },
                ],
                Properties: [
                    { FullName: "Sandbox.Component.Enabled", Name: "Enabled", IsPublic: true, IsProtected: false, IsStatic: false, PropertyType: "bool" },
                ],
                Fields: [],
            },
            {
                FullName: "Sandbox.GameObject",
                Name: "GameObject",
                Namespace: "Sandbox",
                IsPublic: true,
                IsClass: true,
                Documentation: { Summary: "An object in the scene." },
                Methods: [
                    { FullName: "Sandbox.GameObject.Clone", Name: "Clone", IsPublic: true, IsProtected: false, IsStatic: false, IsExtension: false, ReturnType: "GameObject", Parameters: [] },
                ],
            },
        ];

        search.buildIndex(testTypes);

        assert("typeCount is 2 after buildIndex", search.typeCount === 2);
        assert("search for 'Component' returns results", search.search("Component").length > 0);
        assert("search result has fullName", search.search("Component")[0]?.fullName === "Sandbox.Component");
        assert("getType by FullName works", search.getType("Sandbox.Component")?.Name === "Component");
        assert("getType by short Name works", search.getType("Component")?.Name === "Component");
        assert("topMembers includes OnStart", search.search("Component")[0]?.topMembers.includes("OnStart") ?? false);

        // Test formatTypeDetail
        const detail = formatTypeDetail(testTypes[0]!, 0, 10000);
        assert("formatTypeDetail contains type name", detail.includes("Sandbox.Component"));
        assert("formatTypeDetail contains summary", detail.includes("Base class for all components."));
        assert("formatTypeDetail contains method", detail.includes("OnStart"));
        assert("formatTypeDetail contains property", detail.includes("Enabled"));

        return { passed, failed };
    }
}
