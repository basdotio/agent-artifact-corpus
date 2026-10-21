/**
 * Endpoint validation utilities
 * Tests that captured endpoints actually work before publishing to directory
 */

import { Effect } from "effect";
import { StoreError } from "../domain/Errors.js";

export interface ValidationResult {
	endpoint: string;
	method: string;
	status: number;
	ok: boolean;
	responseTime: number;
	error?: string;
}

export interface SiteValidation {
	domain: string;
	totalEndpoints: number;
	validatedEndpoints: number;
	failedEndpoints: number;
	results: ValidationResult[];
	overallValid: boolean;
}

/**
 * Validate a single endpoint by making a test request
 */
export async function validateEndpoint(
	baseUrl: string,
	method: string,
	path: string,
	timeout = 10000,
): Promise<ValidationResult> {
	const url = new URL(path, baseUrl).toString();
	const start = Date.now();

	try {
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), timeout);

		const response = await fetch(url, {
			method: method === "GET" ? "GET" : "HEAD", // Don't POST/PUT/DELETE during validation
			signal: controller.signal,
			headers: {
				"User-Agent": "unsurf-validator/1.0",
				Accept: "application/json, text/html, */*",
			},
		});

		clearTimeout(timeoutId);
		const responseTime = Date.now() - start;

		return {
			endpoint: path,
			method,
			status: response.status,
			ok: response.ok,
			responseTime,
		};
	} catch (err) {
		const responseTime = Date.now() - start;
		return {
			endpoint: path,
			method,
			status: 0,
			ok: false,
			responseTime,
			error: err instanceof Error ? err.message : String(err),
		};
	}
}

/**
 * Validate multiple endpoints for a site
 * Returns true if at least minValid endpoints respond successfully
 */
export async function validateSite(
	domain: string,
	endpoints: Array<{ method: string; path: string }>,
	minValid = 1,
): Promise<SiteValidation> {
	const baseUrl = `https://${domain}`;
	const results: ValidationResult[] = [];

	for (const ep of endpoints.slice(0, 10)) {
		// Limit to first 10 endpoints
		const result = await validateEndpoint(baseUrl, ep.method, ep.path);
		results.push(result);

		// Small delay between requests to be polite
		await new Promise((r) => setTimeout(r, 200));
	}

	const validatedEndpoints = results.filter((r) => r.ok).length;
	const failedEndpoints = results.filter((r) => !r.ok).length;

	return {
		domain,
		totalEndpoints: endpoints.length,
		validatedEndpoints,
		failedEndpoints,
		results,
		overallValid: validatedEndpoints >= minValid,
	};
}

/**
 * Effect wrapper for validation
 */
export const validateSiteEffect = (
	domain: string,
	endpoints: Array<{ method: string; path: string }>,
	minValid = 1,
) =>
	Effect.tryPromise({
		try: () => validateSite(domain, endpoints, minValid),
		catch: (e) => new StoreError({ message: `Validation failed: ${e}` }),
	});
