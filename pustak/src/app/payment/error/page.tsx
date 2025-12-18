"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { XCircle, ArrowLeft, AlertTriangle, RefreshCw } from "lucide-react";
import Link from "next/link";

function PaymentErrorContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const reason = searchParams.get('reason');
  const orderId = searchParams.get('order_id');
  const errorMsg = searchParams.get('error');

  const getErrorMessage = () => {
    switch (reason) {
      case 'payment_failed':
        return errorMsg || 'Your payment could not be processed. Please try again.';
      case 'user_cancelled':
        return 'Payment was cancelled. No charges were made.';
      case 'verification_failed':
        return 'Payment verification failed. Please contact support with your order ID.';
      case 'verification_error':
        return 'An error occurred while verifying your payment. Please contact support.';
      default:
        return 'An error occurred during payment. Please try again.';
    }
  };

  const getErrorTitle = () => {
    switch (reason) {
      case 'payment_failed':
        return 'Payment Failed';
      case 'user_cancelled':
        return 'Payment Cancelled';
      case 'verification_failed':
        return 'Verification Failed';
      default:
        return 'Payment Error';
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
        <div className="max-w-md w-full">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
            {/* Error Icon */}
            <div className="w-20 h-20 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-12 h-12 text-red-600 dark:text-red-400" />
            </div>

            {/* Error Message */}
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              {getErrorTitle()}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {getErrorMessage()}
            </p>

            {/* Order Details */}
            {orderId && (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-6 text-left">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
                      Order Reference
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Order ID: <span className="font-mono">{orderId}</span>
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                      Please save this order ID if you need to contact support.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-col gap-3">
              {reason === 'payment_failed' || reason === 'verification_error' ? (
                <button
                  onClick={() => router.push('/pricing')}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </button>
              ) : (
                <button
                  onClick={() => router.push('/pricing')}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to Pricing
                </button>
              )}
              <Link
                href="/dashboard"
                className="px-6 py-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg font-semibold transition-colors"
              >
                Go to Dashboard
              </Link>
            </div>

            {/* Support Info */}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Need help?
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Contact our support team with your order ID if the problem persists.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default function PaymentErrorPage() {
  return (
    <Suspense fallback={
      <Layout>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    }>
      <PaymentErrorContent />
    </Suspense>
  );
}
