import { Schema } from "effect";

export class NetworkEvent extends Schema.Class<NetworkEvent>("NetworkEvent")({
	requestId: Schema.String,
	url: Schema.String,
	method: Schema.String,
	resourceType: Schema.String,
	requestHeaders: Schema.Record({ key: Schema.String, value: Schema.String }),
	requestBody: Schema.optional(Schema.String),
	responseStatus: Schema.Number,
	responseHeaders: Schema.Record({ key: Schema.String, value: Schema.String }),
	responseBody: Schema.optional(Schema.String),
	timestamp: Schema.Number,
}) {}

/** Resource types we care about — skip images, fonts, stylesheets, etc. */
export const API_RESOURCE_TYPES = new Set(["fetch", "xhr", "document", "websocket", "other"]);

/** URL patterns to always skip */
export const IGNORED_URL_PATTERNS = [
	/\.png$/i,
	/\.jpg$/i,
	/\.jpeg$/i,
	/\.gif$/i,
	/\.svg$/i,
	/\.webp$/i,
	/\.ico$/i,
	/\.css$/i,
	/\.woff2?$/i,
	/\.ttf$/i,
	/\.eot$/i,
	/fonts\.googleapis\.com/i,
	/google-analytics\.com/i,
	/googletagmanager\.com/i,
	/facebook\.net/i,
	/doubleclick\.net/i,
	/hotjar\.com/i,
	/sentry\.io/i,
];

export function isApiRequest(resourceType: string, url: string): boolean {
	if (!API_RESOURCE_TYPES.has(resourceType)) return false;
	return !IGNORED_URL_PATTERNS.some((p) => p.test(url));
}
