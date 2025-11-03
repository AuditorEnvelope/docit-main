import { Layout } from "@/components/Layout";
import { Check, Zap, Users, Building2, ArrowRight } from "lucide-react";
import Link from "next/link";
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Choose the perfect plan for your documentation needs',
};

export default function PricingPage() {
  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      description: "Perfect for individuals and open source projects",
      icon: Zap,
      color: "blue",
      features: [
        "1 repository",
        "100 searches per day",
        "Basic documentation generation",
        "Community support",
        "Dark mode",
      ],
      cta: "Get Started",
      href: "/",  // Free plan goes to home
      popular: false,
    },
    {
      name: "Basic",
      price: "₹2,900",
      period: "per month",
      description: "For professional developers and small teams",
      icon: Users,
      color: "purple",
      features: [
        "5 repositories",
        "Unlimited searches",
        "AI-powered Q&A",
        "Advanced documentation",
        "Priority support",
        "Custom branding",
        "Version history",
      ],
      cta: "Start Free Trial",
      href: "/checkout?plan=basic&org=",
      popular: true,
    },
    {
      name: "Premium",
      price: "₹9,900",
      period: "per month",
      description: "For growing teams and organizations",
      icon: Building2,
      color: "green",
      features: [
        "20 repositories",
        "Unlimited searches",
        "AI-powered Q&A",
        "Team collaboration",
        "Admin overlays",
        "SSO (SAML)",
        "Priority support",
        "Custom domain",
        "Advanced analytics",
      ],
      cta: "Start Free Trial",
      href: "/checkout?plan=premium&org=",
      popular: false,
    },
    {
      name: "Enterprise",
      price: "₹49,900",
      period: "per month",
      description: "For large organizations with custom needs",
      icon: Building2,
      color: "orange",
      features: [
        "Unlimited repositories",
        "Unlimited everything",
        "Dedicated support",
        "SLA guarantee",
        "Custom integrations",
        "On-premise deployment",
        "Advanced security",
        "Custom training",
        "Account manager",
      ],
      cta: "Contact Sales",
      href: "/contact?plan=enterprise",
      popular: false,
    },
  ];

  const getColorClasses = (color: string, type: 'bg' | 'text' | 'border') => {
    const colors = {
      blue: {
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        text: 'text-blue-600 dark:text-blue-400',
        border: 'border-blue-200 dark:border-blue-800',
      },
      purple: {
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        text: 'text-purple-600 dark:text-purple-400',
        border: 'border-purple-200 dark:border-purple-800',
      },
      green: {
        bg: 'bg-green-50 dark:bg-green-900/20',
        text: 'text-green-600 dark:text-green-400',
        border: 'border-green-200 dark:border-green-800',
      },
      orange: {
        bg: 'bg-orange-50 dark:bg-orange-900/20',
        text: 'text-orange-600 dark:text-orange-400',
        border: 'border-orange-200 dark:border-orange-800',
      },
    };
    return colors[color as keyof typeof colors][type];
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-800 dark:to-gray-900 py-16">
          <div className="max-w-7xl mx-auto px-6 text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Simple, Transparent Pricing
            </h1>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              Choose the perfect plan for your documentation needs. All plans include a 14-day free trial.
            </p>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {plans.map((plan) => {
              const Icon = plan.icon;
              return (
                <div
                  key={plan.name}
                  className={`relative bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 ${
                    plan.popular
                      ? 'border-purple-500 dark:border-purple-400'
                      : 'border-gray-200 dark:border-gray-700'
                  } p-8 flex flex-col`}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-purple-600 text-white text-sm font-semibold rounded-full">
                      Most Popular
                    </div>
                  )}

                  {/* Icon */}
                  <div className={`w-12 h-12 rounded-lg ${getColorClasses(plan.color, 'bg')} flex items-center justify-center mb-4`}>
                    <Icon className={`w-6 h-6 ${getColorClasses(plan.color, 'text')}`} />
                  </div>

                  {/* Plan Name */}
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                    {plan.name}
                  </h3>

                  {/* Price */}
                  <div className="mb-4">
                    <span className="text-4xl font-bold text-gray-900 dark:text-gray-100">
                      {plan.price}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400 ml-2">
                      {plan.period}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    {plan.description}
                  </p>

                  {/* Features */}
                  <ul className="space-y-3 mb-8 flex-1">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2">
                        <Check className={`w-5 h-5 ${getColorClasses(plan.color, 'text')} flex-shrink-0 mt-0.5`} />
                        <span className="text-gray-700 dark:text-gray-300 text-sm">
                          {feature}
                        </span>
                      </li>
                    ))}
                  </ul>

                  {/* CTA Button */}
                  <Link
                    href={plan.href}
                    className={`w-full py-3 px-6 rounded-lg font-semibold text-center transition-colors flex items-center justify-center gap-2 ${
                      plan.popular
                        ? 'bg-purple-600 hover:bg-purple-700 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100'
                    }`}
                  >
                    {plan.cta}
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              );
            })}
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-8 text-center">
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Can I change plans later?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we&apos;ll prorate the difference.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                What payment methods do you accept?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                We accept all major credit cards, debit cards, UPI, Netbanking, and wallets via Razorpay. Enterprise plans can also pay via invoice.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Is there a free trial?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Yes! All paid plans come with a 14-day free trial. No credit card required to start.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Can I cancel anytime?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Absolutely! You can cancel your subscription at any time from your billing dashboard. No questions asked.
              </p>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-br from-purple-600 to-blue-600 py-16">
          <div className="max-w-4xl mx-auto px-6 text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to get started?
            </h2>
            <p className="text-xl text-purple-100 mb-8">
              Join thousands of developers using Pustak for their documentation needs.
            </p>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </div>
    </Layout>
  );
}
