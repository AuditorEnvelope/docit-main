import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
	process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
	try {
		const body = await request.json();
		const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = body;

		if (!razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
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

		if (!token) {
			return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
		}

		const response = await fetch(`${BACKEND_URL}/subscriptions/verify-payment`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify(body),
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail || "Failed to verify payment");
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
