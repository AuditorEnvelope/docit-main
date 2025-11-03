"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Layout } from "@/components/Layout";
import { Github, Loader2, Shield, Zap, Lock } from "lucide-react";
import { useAuth } from '@/contexts/AuthContext';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, loading } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, loading, router]);

  const handleGitHubLogin = async () => {
    setIsLoggingIn(true);
    
    try {
      // Get OAuth URL from backend
      const redirectUri = `${window.location.origin}/auth/callback`;
      const response = await fetch(
        `${BACKEND_URL}/auth/github?redirect_uri=${encodeURIComponent(redirectUri)}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to get OAuth URL');
      }
      
      const data = await response.json();
      
      // Redirect to GitHub OAuth
      window.location.href = data.url;
    } catch (error) {
      console.error('Login error:', error);
      setIsLoggingIn(false);
      alert('Failed to start login. Please try again.');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="container mx-auto px-4 py-20">
          <div className="max-w-md mx-auto">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-2xl mb-4">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Welcome to Pustak
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                AI-powered documentation platform
              </p>
            </div>

            {/* Login Card */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
              {/* Benefits */}
              <div className="space-y-4 mb-8">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      Instant Documentation
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      AI generates comprehensive docs from your code
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Github className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      GitHub Integration
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Seamless sync with your repositories
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Lock className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      Secure & Private
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Your code stays private, we only read metadata
                    </p>
                  </div>
                </div>
              </div>

              {/* Login Button */}
              <button
                onClick={handleGitHubLogin}
                disabled={isLoggingIn}
                className="w-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 py-4 rounded-xl font-semibold hover:bg-gray-800 dark:hover:bg-gray-100 transition-all duration-200 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
              >
                {isLoggingIn ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Connecting to GitHub...
                  </>
                ) : (
                  <>
                    <Github className="w-5 h-5" />
                    Continue with GitHub
                  </>
                )}
              </button>

              {/* Privacy Note */}
              <p className="text-xs text-center text-gray-500 dark:text-gray-400 mt-6">
                By continuing, you agree to our{' '}
                <a href="/terms" className="underline hover:text-gray-700 dark:hover:text-gray-300">
                  Terms of Service
                </a>{' '}
                and{' '}
                <a href="/privacy" className="underline hover:text-gray-700 dark:hover:text-gray-300">
                  Privacy Policy
                </a>
              </p>
            </div>

            {/* Free Plan Note */}
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                🎉 Start with our <span className="font-semibold text-blue-600 dark:text-blue-400">Free Plan</span>
                {' '}— No credit card required
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
