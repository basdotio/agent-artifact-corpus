import { Schema } from "effect";

/**
 * Auth type detected from captured traffic
 */
export const AuthType = Schema.Literal(
	"none",
	"bearer",
	"cookie",
	"api-key",
	"oauth",
	"basic",
	"unknown",
);
export type AuthType = typeof AuthType.Type;

/**
 * Capability categories for auto-classification
 */
export const Capability = Schema.Literal(
	"auth",
	"payments",
	"content",
	"crud",
	"search",
	"messaging",
	"files",
	"analytics",
	"social",
	"ecommerce",
	"forms",
	"other",
);
export type Capability = typeof Capability.Type;

/**
 * Fingerprint — the atomic unit for agent discovery
 * ~50 tokens, enough to decide "is this what I need?"
 */
export class Fingerprint extends Schema.Class<Fingerprint>("Fingerprint")({
	domain: Schema.String,
	url: Schema.String,
	endpoints: Schema.Number,
	capabilities: Schema.Array(Capability),
	methods: Schema.Record({ key: Schema.String, value: Schema.Number }),
	auth: AuthType,
	confidence: Schema.Number,
	lastScouted: Schema.String,
	version: Schema.Number,
	specUrl: Schema.String,
}) {}

/**
 * EndpointSummary — single endpoint detail
 * ~80 tokens with schema, used for surgical lookups
 */
export class EndpointSummary extends Schema.Class<EndpointSummary>("EndpointSummary")({
	method: Schema.String,
	path: Schema.String,
	summary: Schema.String,
	requestSchema: Schema.optionalWith(Schema.Unknown, { as: "Option" }),
	responseSchema: Schema.Unknown,
	auth: Schema.Boolean,
	example: Schema.optionalWith(
		Schema.Struct({
			request: Schema.Unknown,
			response: Schema.Unknown,
		}),
		{ as: "Option" },
	),
}) {}

/**
 * CapabilitySlice — grouped endpoints by capability
 * ~200 tokens, used for "show me payment endpoints"
 */
export class CapabilitySlice extends Schema.Class<CapabilitySlice>("CapabilitySlice")({
	domain: Schema.String,
	capability: Capability,
	endpoints: Schema.Array(EndpointSummary),
}) {}

/**
 * SearchResult — returned from semantic search
 * ~30 tokens per result
 */
export class SearchResult extends Schema.Class<SearchResult>("SearchResult")({
	domain: Schema.String,
	match: Schema.String,
	capability: Capability,
	confidence: Schema.Number,
	specUrl: Schema.String,
}) {}
