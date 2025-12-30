import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
	process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
	try {
		const body = await request.json();
		const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = body;

		if (!razorpay_order_id || !razorpay_payment_id) {
			return NextResponse.json(
				{ error: "Missing required payment details" },
				{ status: 400 }
			);
		}

		const authHeader =
			request.headers.get("authorization") ||
			request.headers.get("Authorization");
		const token =
			request.cookies.get("auth_token")?.value ||
			authHeader?.replace(/^Bearer\s+/i, "");

		console.log("[VERIFY-PAYMENT] Auth header:", authHeader);
		console.log(
			"[VERIFY-PAYMENT] Token from cookies:",
			request.cookies.get("auth_token")?.value
		);
		console.log(
			"[VERIFY-PAYMENT] Token from header:",
			authHeader?.replace(/^Bearer\s+/i, "")
		);
		console.log("[VERIFY-PAYMENT] Final token:", token);

		if (!token) {
			console.log("[VERIFY-PAYMENT] No token found, returning 401");
			return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
		}

		// Check if BACKEND_URL already includes the API prefix
		const backendUrl = BACKEND_URL.endsWith("/api/v1")
			? BACKEND_URL
			: `${BACKEND_URL}/api/v1`;
		const fullUrl = `${backendUrl}/subscriptions/verify-payment`;

		console.log("[VERIFY-PAYMENT] Backend URL:", BACKEND_URL);
		console.log("[VERIFY-PAYMENT] Backend URL with API prefix:", backendUrl);
		console.log("[VERIFY-PAYMENT] Full URL:", fullUrl);
		console.log("[VERIFY-PAYMENT] Request body:", body);
		console.log(
			"[VERIFY-PAYMENT] Authorization header:",
			`Bearer ${token.substring(0, 10)}...`
		); // Only log first 10 chars for security

		const response = await fetch(fullUrl, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify(body),
		});

		console.log("[VERIFY-PAYMENT] Backend response status:", response.status);
		console.log(
			"[VERIFY-PAYMENT] Backend response headers:",
			Object.fromEntries(response.headers.entries())
		);

		if (!response.ok) {
			// Try to get JSON error response, fallback to text if not available
			let errorData;
			const contentType = response.headers.get("content-type");

			if (contentType && contentType.includes("application/json")) {
				try {
					errorData = await response.json();
				} catch {
					errorData = { detail: "Failed to parse error response" };
				}
			} else {
				// If not JSON, get text response
				const errorText = await response.text();
				errorData = { detail: errorText || `HTTP Error ${response.status}` };
			}

			throw new Error(errorData.detail || `HTTP Error ${response.status}`);
		}

		const data = await response.json();
		return NextResponse.json(data);
	} catch (error: any) {
		console.error("Payment verification error:", error);
		return NextResponse.json(
			{ error: error.message || "Failed to verify payment" },
			{ status: 500 }
		);
	}
}
