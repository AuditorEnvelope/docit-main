import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
	process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
	try {
		const body = await request.json();
		const { plan } = body;
		// orgName is optional - backend will auto-generate from user email

		if (!plan) {
			return NextResponse.json(
				{ error: "Missing required field: plan" },
				{ status: 400 }
			);
		}

		// Get auth token from cookie or header
		const authHeader =
			request.headers.get("authorization") ||
			request.headers.get("Authorization");
		const token =
			request.cookies.get("auth_token")?.value ||
			authHeader?.replace(/^Bearer\s+/i, "");

		if (!token) {
			return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
		}

		// Call backend to create Razorpay order
		const response = await fetch(`${BACKEND_URL}/api/checkout/create`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify({
				plan_name: plan,
				// org_name is optional - backend will auto-generate from user email
				success_url: `${request.nextUrl.origin}/dashboard?checkout=success`,
				cancel_url: `${request.nextUrl.origin}/pricing?checkout=cancelled`,
			}),
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail || "Failed to create checkout session");
		}

		const data = await response.json();
		return NextResponse.json(data);
	} catch (error: any) {
		console.error("Checkout error:", error);
		return NextResponse.json(
			{ error: error.message || "Failed to create checkout session" },
			{ status: 500 }
		);
	}
}
