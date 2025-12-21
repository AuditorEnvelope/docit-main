"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { Loader2, CreditCard, AlertCircle } from "lucide-react";

declare global {
	interface Window {
		Razorpay: any;
	}
}

function CheckoutContent() {
	const searchParams = useSearchParams();
	const router = useRouter();
	const [loading, setLoading] = useState(true);
	const [verifying, setVerifying] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const plan = searchParams.get("plan");

	useEffect(() => {
		const script = document.createElement("script");
		script.src = "https://checkout.razorpay.com/v1/checkout.js";
		script.async = true;
		script.onload = initiateCheckout;
		script.onerror = () => {
			setError("Failed to load Razorpay. Please check your internet connection.");
			setLoading(false);
		};
		document.body.appendChild(script);

		async function initiateCheckout() {
			if (!plan) {
				setError("No plan selected");
				setLoading(false);
				return;
			}

			if (!window.Razorpay) {
				setError("Razorpay script not loaded yet. Please wait.");
				return;
			}

			try {
				let token = localStorage.getItem("pustak_access_token");
				if (!token) {
					const authCookie = document.cookie.split("; ").find(row => row.startsWith('auth_token='));
					if (authCookie) {
						token = authCookie.split('=')[1];
					}
				}

				if (!token) {
					setError("Authentication required. Please log in.");
					setLoading(false);
					router.push("/login");
					return;
				}

				const response = await fetch("/api/create-checkout", {
					method: "POST",
					headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
					credentials: "include",
					body: JSON.stringify({ plan }),
				});

				if (!response.ok) {
					const errorData = await response.json().catch(() => ({}));
					throw new Error(errorData.error || "Failed to create Razorpay order");
				}

				const orderData = await response.json();

				const options = {
					key: orderData.key_id,
					amount: orderData.amount,
					currency: orderData.currency || "INR",
					name: "Lekhak AI",
					description: `Subscription: ${plan} Plan`,
					order_id: orderData.order_id,
					handler: async (paymentResponse: any) => {
						setVerifying(true);
						try {
							const verifyResponse = await fetch("/api/verify-payment", {
								method: "POST",
								headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
								credentials: "include",
								body: JSON.stringify(paymentResponse),
							});
							if (!verifyResponse.ok) {
								const errorData = await verifyResponse.json().catch(() => ({}));
								throw new Error(errorData.error || "Payment verification failed");
							}
							router.push(`/payment/success?order_id=${paymentResponse.razorpay_order_id}&payment_id=${paymentResponse.razorpay_payment_id}&plan=${plan}`);
						} catch (err: any) {
							router.push(`/payment/error?reason=verification_error&order_id=${paymentResponse.razorpay_order_id}`);
							setVerifying(false);
						}
					},
					prefill: {
						name: orderData.metadata?.user_name || "",
						email: orderData.metadata?.user_email || "",
					},
					theme: { color: "#3B82F6" },
					modal: {
						ondismiss: () => router.push(`/payment/error?reason=user_cancelled&order_id=${orderData.order_id}`),
					},
				};

				const rzp = new window.Razorpay(options);
				rzp.on("payment.failed", (response: any) => {
					router.push(`/payment/error?reason=payment_failed&order_id=${response.error.metadata?.order_id || orderData.order_id}&error=${encodeURIComponent(response.error.description)}`);
				});

				rzp.open();
				setLoading(false);
			} catch (err: any) {
				setError(err.message || "Failed to start checkout. Please try again.");
				setLoading(false);
			}
		}

		return () => {
			if (script.parentNode) {
				document.body.removeChild(script);
			}
		};
	}, [plan, router]);

	return (
		<Layout>
			<div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
				<div className="max-w-md w-full">
					{loading || verifying ? (
						<div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
							<Loader2 className="w-16 h-16 text-blue-600 dark:text-blue-400 mx-auto mb-6 animate-spin" />
							<h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
								{verifying ? "Verifying Payment" : "Preparing Payment"}
							</h2>
							<p className="text-gray-600 dark:text-gray-400">
								{verifying
									? "Please wait while we confirm your payment..."
									: "Please wait while we prepare your secure payment..."}
							</p>
							<div className="mt-6 flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
								<CreditCard className="w-4 h-4" />
								<span>Powered by Razorpay</span>
							</div>
						</div>
					) : error ? (
						<div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
							<div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
								<AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
							</div>
							<h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
								Checkout Failed
							</h2>
							<p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
							<button
								onClick={() => router.push("/pricing")}
								className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
							>
								Back to Pricing
							</button>
						</div>
					) : null}
				</div>
			</div>
		</Layout>
	);
}

export default function CheckoutPage() {
	return (
		<Suspense fallback={<CheckoutLoadingFallback />}>
			<CheckoutContent />
		</Suspense>
	);
}

function CheckoutLoadingFallback() {
	return (
		<Layout>
			<div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
				<div className="max-w-md w-full">
					<div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
						<Loader2 className="w-16 h-16 text-blue-600 dark:text-blue-400 mx-auto mb-6 animate-spin" />
						<h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
							Loading Checkout...
						</h2>
					</div>
				</div>
			</div>
		</Layout>
	);
}
