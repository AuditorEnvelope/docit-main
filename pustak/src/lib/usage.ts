/**
 * Usage API Client - Phase 4: Frontend Integration
 * =================================================
 *
 * Provides type-safe API client for fetching usage statistics
 * and limits from the ledger-based billing backend.
 *
 * Endpoints:
 * - GET /api/v1/usage/me - Get current cycle usage & limits
 * - GET /api/v1/usage/history - Get usage event history
 * - GET /api/v1/usage/summary - Get raw usage counts
 */

const BACKEND_URL =
	process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

/**
 * Resource types that can be tracked for usage
 */
export type ResourceType =
	| "docs_generated"
	| "repos_connected"
	| "api_calls"
	| "pages_processed"
	| "tokens_used";

/**
 * Subscription plan tiers
 */
export type PlanTier = "free" | "pro" | "team" | "enterprise";

/**
 * Usage limit details for a single resource
 */
export interface ResourceUsage {
	used: number; // Amount consumed in current cycle
	limit: number; // Total allowed by plan (-1 = unlimited)
	remaining: number; // Quota left (-1 if unlimited)
	allowed: boolean; // True if user can consume more
}

/**
 * Complete usage statistics response from /api/v1/usage/me
 */
export interface UsageStats {
	plan: PlanTier;
	subscription_id: string;
	cycle_start: string; // ISO timestamp
	cycle_end: string; // ISO timestamp
	limits: {
		docs_generated?: ResourceUsage;
		repos_connected?: ResourceUsage;
		api_calls?: ResourceUsage;
		pages_processed?: ResourceUsage;
		tokens_used?: ResourceUsage;
	};
}

/**
 * Usage event from history
 */
export interface UsageEvent {
	id: string;
	subscription_id: string;
	user_id: string;
	resource_type: ResourceType;
	amount: number;
	resource_id: string | null;
	consumed_at: string; // ISO timestamp
	created_at: string; // ISO timestamp
}

/**
 * Raw usage summary (simplified)
 */
export interface UsageSummary {
	docs_generated?: number;
	repos_connected?: number;
	api_calls?: number;
	pages_processed?: number;
	tokens_used?: number;
}

/**
 * Error response when usage limit is exceeded (403)
 */
export interface UsageLimitError {
	error: "usage_limit_exceeded";
	message: string;
	plan: PlanTier;
	used: number;
	limit: number;
	cycle_end: string;
	action: "upgrade_or_wait";
}

// ============================================================================
// API CLIENT FUNCTIONS
// ============================================================================

/**
 * Fetch current usage statistics and limits
 *
 * @param token - JWT authentication token
 * @returns Promise<UsageStats> - Current cycle usage data
 * @throws Error if request fails or user is not authenticated
 *
 * @example
 * ```typescript
 * const usage = await fetchUsageStats(token);
 * console.log(`Docs used: ${usage.limits.docs_generated?.used}`);
 * ```
 */
export async function fetchUsageStats(token: string): Promise<UsageStats> {
	const apiBase = BACKEND_URL.endsWith("/api/v1")
		? BACKEND_URL
		: `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

	const response = await fetch(`${apiBase}/usage/me`, {
		method: "GET",
		headers: {
			Authorization: `Bearer ${token}`,
			"Content-Type": "application/json",
		},
		cache: "no-store", // Always fetch fresh data
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error("Authentication required. Please log in.");
		}
		if (response.status === 404) {
			throw new Error(
				"No active subscription found. Please subscribe to a plan."
			);
		}
		const errorData = await response.json().catch(() => ({}));
		throw new Error(
			errorData.detail || `Failed to fetch usage stats: ${response.statusText}`
		);
	}

	const data: UsageStats = await response.json();
	return data;
}

/**
 * Fetch usage event history
 *
 * @param token - JWT authentication token
 * @param options - Optional filters (resource_type, limit)
 * @returns Promise<UsageEvent[]> - Array of usage events
 *
 * @example
 * ```typescript
 * const history = await fetchUsageHistory(token, {
 *   resource_type: 'docs_generated',
 *   limit: 50
 * });
 * ```
 */
export async function fetchUsageHistory(
	token: string,
	options?: {
		resource_type?: ResourceType;
		limit?: number;
	}
): Promise<UsageEvent[]> {
	const apiBase = BACKEND_URL.endsWith("/api/v1")
		? BACKEND_URL
		: `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

	const params = new URLSearchParams();
	if (options?.resource_type) {
		params.append("resource_type", options.resource_type);
	}
	if (options?.limit) {
		params.append("limit", options.limit.toString());
	}

	const url = `${apiBase}/usage/history${
		params.toString() ? `?${params}` : ""
	}`;

	const response = await fetch(url, {
		method: "GET",
		headers: {
			Authorization: `Bearer ${token}`,
			"Content-Type": "application/json",
		},
		cache: "no-store",
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error("Authentication required.");
		}
		throw new Error(`Failed to fetch usage history: ${response.statusText}`);
	}

	const data: UsageEvent[] = await response.json();
	return data;
}

/**
 * Fetch raw usage summary (counts only, no limits)
 *
 * @param token - JWT authentication token
 * @returns Promise<UsageSummary> - Raw usage counts
 *
 * @example
 * ```typescript
 * const summary = await fetchUsageSummary(token);
 * console.log(`Docs: ${summary.docs_generated || 0}`);
 * ```
 */
export async function fetchUsageSummary(token: string): Promise<UsageSummary> {
	const apiBase = BACKEND_URL.endsWith("/api/v1")
		? BACKEND_URL
		: `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

	const response = await fetch(`${apiBase}/usage/summary`, {
		method: "GET",
		headers: {
			Authorization: `Bearer ${token}`,
			"Content-Type": "application/json",
		},
		cache: "no-store",
	});

	if (!response.ok) {
		if (response.status === 401) {
			throw new Error("Authentication required.");
		}
		throw new Error(`Failed to fetch usage summary: ${response.statusText}`);
	}

	const data: UsageSummary = await response.json();
	return data;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Calculate usage percentage
 *
 * @param used - Amount used
 * @param limit - Total limit (-1 = unlimited)
 * @returns Percentage (0-100) or null if unlimited
 *
 * @example
 * ```typescript
 * const percent = getUsagePercentage(73, 1000); // 7.3
 * const unlimited = getUsagePercentage(100, -1); // null
 * ```
 */
export function getUsagePercentage(used: number, limit: number): number | null {
	if (limit === -1) {
		return null; // Unlimited
	}
	if (limit === 0) {
		return 100; // No quota = 100% used
	}
	return Math.min((used / limit) * 100, 100);
}

/**
 * Get color class based on usage percentage
 *
 * @param percentage - Usage percentage (0-100)
 * @returns Tailwind color class string
 *
 * @example
 * ```typescript
 * const color = getUsageColor(85); // 'red'
 * const bgClass = `bg-${color}-500`;
 * ```
 */
export function getUsageColor(
	percentage: number | null
): "green" | "yellow" | "red" {
	if (percentage === null) {
		return "green"; // Unlimited = always green
	}
	if (percentage >= 90) {
		return "red";
	}
	if (percentage >= 80) {
		return "yellow";
	}
	return "green";
}

/**
 * Format number with thousands separator
 *
 * @param num - Number to format
 * @returns Formatted string (e.g., "1,000")
 */
export function formatNumber(num: number): string {
	if (num === -1) {
		return "Unlimited";
	}
	return num.toLocaleString();
}

/**
 * Format date from ISO string to readable format
 *
 * @param isoString - ISO timestamp string
 * @returns Formatted date string
 *
 * @example
 * ```typescript
 * formatDate('2026-01-15T00:00:00Z'); // 'Jan 15, 2026'
 * ```
 */
export function formatDate(isoString: string): string {
	const date = new Date(isoString);
	return date.toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
	});
}

/**
 * Check if error is a usage limit error
 *
 * @param error - Error object from catch block
 * @returns True if this is a 403 usage limit exceeded error
 *
 * @example
 * ```typescript
 * catch (error) {
 *   if (isUsageLimitError(error)) {
 *     showUpgradeModal(error.response.data.detail);
 *   }
 * }
 * ```
 */
export function isUsageLimitError(
	error: any
): error is {
	response: { status: number; data: { detail: UsageLimitError } };
} {
	return (
		error?.response?.status === 403 &&
		error?.response?.data?.detail?.error === "usage_limit_exceeded"
	);
}
