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
  const [error, setError] = useState<string | null>(null);
  
  const plan = searchParams.get('plan');

  useEffect(() => {
    // Load Razorpay script
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onerror = () => {
      setError('Failed to load Razorpay. Please check your internet connection.');
      setLoading(false);
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  useEffect(() => {
    async function initiateCheckout() {
      if (!plan) {
        setError('No plan selected');
        setLoading(false);
        return;
      }

      // Wait for Razorpay script to load
      let retries = 0;
      while (!window.Razorpay && retries < 10) {
        await new Promise(resolve => setTimeout(resolve, 100));
        retries++;
      }

      if (!window.Razorpay) {
        setError('Razorpay failed to load. Please refresh the page.');
        setLoading(false);
        return;
      }

      try {
        // Get org name from URL params or prompt user
        const orgNameParam = searchParams.get('org');
        let orgName = orgNameParam;
        
        // If no org name, prompt user
        if (!orgName) {
          const promptOrg = prompt('Enter organization name for this subscription:');
          if (!promptOrg) {
            setError('Organization name is required');
            setLoading(false);
            return;
          }
          orgName = promptOrg;
        }

        // Get auth token from localStorage or cookies
        let token = localStorage.getItem('pustak_access_token');
        
        // Also try to get from cookies (for server-side API routes)
        if (!token && typeof document !== 'undefined') {
          const cookies = document.cookie.split(';');
          const authCookie = cookies.find(c => c.trim().startsWith('auth_token='));
          if (authCookie) {
            token = authCookie.split('=')[1];
          }
        }
        
        if (!token) {
          setError('Please log in to continue');
          setLoading(false);
          router.push('/login');
          return;
        }

        // Create Razorpay order via backend
        const response = await fetch('/api/create-checkout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            plan,
            orgName,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || 'Failed to create order');
        }

        const orderData = await response.json();
        
        // Initialize Razorpay checkout
        const options = {
          key: orderData.key_id, // Razorpay Key ID
          amount: orderData.amount, // Amount in paise
          currency: orderData.currency || 'INR',
          name: 'Lekhak AI',
          description: `Subscription: ${plan} Plan`,
          order_id: orderData.order_id,
          handler: async function (response: any) {
            // Payment successful - verify and redirect
            try {
              // Get token again for verification
              let verifyToken = localStorage.getItem('pustak_access_token');
              if (!verifyToken && typeof document !== 'undefined') {
                const cookies = document.cookie.split(';');
                const authCookie = cookies.find(c => c.trim().startsWith('auth_token='));
                if (authCookie) {
                  verifyToken = authCookie.split('=')[1];
                }
              }
              
              const verifyResponse = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/payment/verify`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${verifyToken}`,
                },
                credentials: 'include',
                body: JSON.stringify({
                  order_id: response.razorpay_order_id,
                  payment_id: response.razorpay_payment_id,
                  signature: response.razorpay_signature,
                }),
              });

              if (verifyResponse.ok) {
                // Redirect to success page
                router.push(`/payment/success?order_id=${response.razorpay_order_id}&payment_id=${response.razorpay_payment_id}&plan=${plan}&org=${encodeURIComponent(orgName)}`);
              } else {
                // Redirect to error page
                router.push(`/payment/error?reason=verification_failed&order_id=${response.razorpay_order_id}`);
              }
            } catch (err) {
              console.error('Verification error:', err);
              router.push(`/payment/error?reason=verification_error&order_id=${response.razorpay_order_id}`);
            }
          },
          prefill: {
            name: orderData.metadata?.owner_name || '',
            email: orderData.metadata?.owner_email || '',
            contact: orderData.metadata?.owner_phone || '',
          },
          theme: {
            color: '#3B82F6',
          },
          modal: {
            ondismiss: function() {
              // User closed the modal
              router.push(`/payment/error?reason=user_cancelled&order_id=${orderData.order_id}`);
            },
          },
        };

        const razorpay = new window.Razorpay(options);
        razorpay.on('payment.failed', function (response: any) {
          // Payment failed - redirect to error page
          router.push(`/payment/error?reason=payment_failed&order_id=${response.error.metadata?.order_id || orderData.order_id}&error=${encodeURIComponent(response.error.description)}`);
        });

        razorpay.open();
        setLoading(false);

      } catch (err: any) {
        console.error('Checkout error:', err);
        setError(err.message || 'Failed to start checkout. Please try again.');
        setLoading(false);
      }
    }

    if (window.Razorpay) {
      initiateCheckout();
    }
  }, [plan, searchParams, router]);

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-6">
        <div className="max-w-md w-full">
          {loading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
              <Loader2 className="w-16 h-16 text-blue-600 dark:text-blue-400 mx-auto mb-6 animate-spin" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Preparing Payment
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we prepare your secure payment...
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