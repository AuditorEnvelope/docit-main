"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { CheckCircle, ArrowRight, Package } from "lucide-react";
import Link from "next/link";

function PaymentSuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  
  const orderId = searchParams.get('order_id');
  const paymentId = searchParams.get('payment_id');
  const plan = searchParams.get('plan');
  const org = searchParams.get('org');

  useEffect(() => {
    // Simulate processing
    setTimeout(() => {
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Processing your payment...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
        <div className="max-w-md w-full">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
            {/* Success Icon */}
            <div className="w-20 h-20 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-12 h-12 text-green-600 dark:text-green-400" />
            </div>

            {/* Success Message */}
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Payment Successful! 🎉
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Your subscription has been activated successfully.
            </p>

            {/* Plan Info */}
            {plan && (
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Package className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <span className="font-semibold text-blue-900 dark:text-blue-100">
                    {plan.charAt(0).toUpperCase() + plan.slice(1)} Plan
                  </span>
                </div>
                {org && (
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Organization: {org}
                  </p>
                )}
              </div>
            )}

            {/* Payment Details */}
            {(orderId || paymentId) && (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-6 text-left">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Payment Details
                </h3>
                {orderId && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Order ID: <span className="font-mono">{orderId}</span>
                  </p>
                )}
                {paymentId && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Payment ID: <span className="font-mono">{paymentId}</span>
                  </p>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-col gap-3">
              <Link
                href="/dashboard"
                className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
              >
                Go to Dashboard
                <ArrowRight className="w-4 h-4" />
              </Link>
              <button
                onClick={() => router.push('/pricing')}
                className="px-6 py-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg font-semibold transition-colors"
              >
                View Plans
              </button>
            </div>

            {/* Info */}
            <p className="mt-6 text-xs text-gray-500 dark:text-gray-400">
              A confirmation email will be sent to your registered email address.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={
      <Layout>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    }>
      <PaymentSuccessContent />
    </Suspense>
  );
}
