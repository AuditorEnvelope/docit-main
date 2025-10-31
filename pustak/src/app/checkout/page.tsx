"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { Loader2, CreditCard, CheckCircle } from "lucide-react";

function CheckoutContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const plan = searchParams.get('plan');

  useEffect(() => {
    async function initiateCheckout() {
      if (!plan) {
        setError('No plan selected');
        setLoading(false);
        return;
      }

      try {
        // For demo: using mock user data
        // In production: get from auth session
        const userId = 'demo-user-' + Date.now();
        const userEmail = 'demo@example.com';

        const response = await fetch('/api/create-checkout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            plan,
            userId,
            userEmail,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to create checkout session');
        }

        const data = await response.json();
        
        // Redirect to Stripe Checkout
        if (data.url) {
          window.location.href = data.url;
        } else {
          throw new Error('No checkout URL received');
        }
        
      } catch (err) {
        console.error('Checkout error:', err);
        setError('Failed to start checkout. Please try again.');
        setLoading(false);
      }
    }

    initiateCheckout();
  }, [plan]);

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
        <div className="max-w-md w-full">
          {loading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
              <Loader2 className="w-16 h-16 text-blue-600 dark:text-blue-400 mx-auto mb-6 animate-spin" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Redirecting to Checkout
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we prepare your secure payment...
              </p>
              <div className="mt-6 flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <CreditCard className="w-4 h-4" />
                <span>Powered by Stripe</span>
              </div>
            </div>
          ) : error ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-3xl">❌</span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Checkout Failed
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {error}
              </p>
              <button
                onClick={() => router.push('/pricing')}
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
              Loading...
            </h2>
          </div>
        </div>
      </div>
    </Layout>
  );
}
