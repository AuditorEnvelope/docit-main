# Add Stripe Integration for Monetization

**Type:** feature  
**Significance:** 8/10  
**Date:** 2025-10-22 11:01:50 UTC  
**Commit:** 5be4502f51f605cd3e928ab4045cceea8f7ab8d1  
**Branch:** refs/heads/main  

This document outlines the changes introduced for Stripe integration, a significant feature for enabling monetization within the application.

---

# Documentation: Stripe Integration for Monetization

## 1. Overview

This release introduces a major new feature: the integration of Stripe as our primary payment gateway. This enhancement is crucial for enabling monetization strategies, allowing the application to process payments for various products, services, or subscription tiers. The primary goal is to establish a robust and secure system for handling transactions, thereby creating new revenue streams for the project.

The changes primarily involve the configuration necessary to connect the application with the Stripe platform, including the setup of API keys and specific price identifiers for our offerings.

## 2. Impact

This feature significantly impacts the following areas of the system:

*   **Payments**: All payment processing will now leverage Stripe's secure infrastructure. This affects how users interact with checkout flows and how transactions are managed internally.
*   **Monetization**: This integration forms the foundation for all future monetization efforts, enabling the sale of products, subscriptions, or other premium content.
*   **Stripe Integration**: The system now has a dedicated interface and configuration for interacting with the Stripe API and webhooks.

Specifically, the core change introduced in the codebase is the addition of new environment variables within the `pustak/.env.local.example` file. Developers will need to update their local environment configurations (`.env.local`) to include these variables to enable Stripe functionality.

## 3. New Features

The following new functionalities have been added:

*   **Stripe Payment Gateway**: The application now supports secure payment processing through Stripe, allowing users to make purchases using various payment methods supported by Stripe.
*   **Stripe Configuration**: A structured way to configure the application's connection to Stripe using API keys (publishable and secret keys) and webhook secrets. This ensures secure and authenticated communication with Stripe's services.
*   **Price IDs**: The ability to define and use specific Stripe Price IDs. These identifiers link directly to products and pricing models configured within your Stripe Dashboard, enabling dynamic pricing and product management from the Stripe platform itself.

## 4. Breaking Changes

**None.**

This feature is purely additive and does not introduce any breaking changes to existing functionalities or APIs. Existing parts of the application will continue to function as before.

## 5. Technical Details

The core technical implementation involves adding necessary Stripe configuration parameters as environment variables. These variables are crucial for authenticating requests to Stripe and for identifying specific products or services available for purchase.

The following new entries have been added to the `pustak/.env.local.example` file:

```
# Stripe Integration
# Visit https://dashboard.stripe.com/test/apikeys to get your API keys
# And https://dashboard.stripe.com/test/webhooks to configure webhooks
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_STRIPE_PUBLISHABLE_KEY
STRIPE_SECRET_KEY=sk_test_YOUR_STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_STRIPE_WEBHOOK_SECRET

# Example Stripe Price IDs for different tiers/products
# These should correspond to prices created in your Stripe Dashboard
STRIPE_PRICE_ID_PREMIUM=price_YOUR_PREMIUM_PRICE_ID
STRIPE_PRICE_ID_PRO=price_YOUR_PRO_PRICE_ID
```

*   `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`: This key is safe to be exposed in the frontend and is used by Stripe.js to create secure payment elements and tokens.
*   `STRIPE_SECRET_KEY`: This key must be kept secret and should only be used on the backend (server-side) to make authenticated API calls to Stripe (e.g., creating checkout sessions, managing subscriptions).
*   `STRIPE_WEBHOOK_SECRET`: Used to verify the authenticity of webhook events sent from Stripe to your application, preventing spoofed requests.
*   `STRIPE_PRICE_ID_PREMIUM`, `STRIPE_PRICE_ID_PRO`: These are placeholders for actual Stripe Price IDs. Each Price ID uniquely identifies a product or service with a specific pricing model (e.g., monthly subscription, one-time purchase) configured in your Stripe Dashboard. The application will use these IDs to initiate checkout processes for corresponding offerings.

## 6. Usage Examples

To utilize the new Stripe integration, developers must configure their local environment and ensure the application correctly references these new variables.

### 6.1. Environment Configuration

1.  **Obtain Stripe API Keys and Webhook Secret:**
    *   Navigate to your Stripe Dashboard ([https://dashboard.stripe.com/](https://dashboard.stripe.com/)).
    *   Go to **Developers > API keys** to find your **Publishable key** and **Secret key**.
    *   Go to **Developers > Webhooks** to create an endpoint and obtain your **Webhook secret**.
    *   Make sure to toggle between "Test mode" and "Live mode" as appropriate for your environment.

2.  **Create Price IDs in Stripe:**
    *   In your Stripe Dashboard, go to **Products**.
    *   Create new products and add pricing plans (e.g., a "Premium Plan" for $10/month, a "Pro Plan" for $25/month).
    *   Note down the **Price ID** for each pricing plan you create (e.g., `price_12345ABCDEF`).

3.  **Update `.env.local`:**
    *   Copy the new Stripe-related variables from `pustak/.env.local.example` to your `pustak/.env.local` file.
    *   Replace the placeholder values with your actual Stripe API keys, webhook secret, and Price IDs.

    ```bash
    # pustak/.env.local
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_ACTUAL_STRIPE_PUBLISHABLE_KEY_FROM_DASHBOARD
    STRIPE_SECRET_KEY=sk_test_YOUR_ACTUAL_STRIPE_SECRET_KEY_FROM_DASHBOARD
    STRIPE_WEBHOOK_SECRET=whsec_YOUR_ACTUAL_STRIPE_WEBHOOK_SECRET_FROM_DASHBOARD
    STRIPE_PRICE_ID_PREMIUM=price_ACTUAL_PREMIUM_PRICE_ID_FROM_STRIPE
    STRIPE_PRICE_ID_PRO=price_ACTUAL_PRO_PRICE_ID_FROM_STRIPE
    ```

### 6.2. Application Usage

Once configured, the application components will leverage these environment variables:

*   **Frontend (Stripe.js):** The `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` will be used to initialize the Stripe.js client library, enabling client-side payment element rendering and tokenization.

    ```javascript
    // Example in a React component
    import { loadStripe } from '@stripe/stripe-js';

    const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY);

    // Later, to render Elements:
    // const stripe = await stripePromise;
    // const elements = stripe.elements();
    // const cardElement = elements.create('card');
    // cardElement.mount('#card-element');
    ```

*   **Backend (Server-side API routes/handlers):** The `STRIPE_SECRET_KEY` will be used to make authenticated calls to the Stripe API, such as creating checkout sessions, fetching customer details, or processing refunds. The `STRIPE_PRICE_ID_PREMIUM` and `STRIPE_PRICE_ID_PRO` will be used when creating checkout sessions to specify which product/plan the user is purchasing.

    ```javascript
    // Example in a Next.js API route (api/checkout.js)
    import Stripe from 'stripe';

    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: '2022-11-15', // or your desired API version
    });

    export default async function handler(req, res) {
      if (req.method === 'POST') {
        try {
          const { quantity } = req.body;
          const session = await stripe.checkout.sessions.create({
            line_items: [
              {
                price: process.env.STRIPE_PRICE_ID_PREMIUM, // Use the configured Price ID
                quantity: quantity || 1,
              },
            ],
            mode: 'payment', // or 'subscription'
            success_url: `${req.headers.origin}/success?session_id={CHECKOUT_SESSION_ID}`,
            cancel_url: `${req.headers.origin}/cancel`,
          });
          res.redirect(303, session.url);
        } catch (err) {
          res.status(err.statusCode || 500).json(err.message);
        }
      } else {
        res.setHeader('Allow', 'POST');
        res.status(405).end('Method Not Allowed');
      }
    }
    ```

*   **Webhooks:** The `STRIPE_WEBHOOK_SECRET` is used in a dedicated webhook endpoint to verify the signature of incoming webhook events from Stripe, ensuring their integrity and origin.

    ```javascript
    // Example in a Next.js API route (api/webhooks.js)
    import Stripe from 'stripe';
    import { buffer } from 'micro';

    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
        apiVersion: '2022-11-15',
    });

    export const config = {
        api: {
            bodyParser: false,
        },
    };

    export default async function handler(req, res) {
        if (req.method === 'POST') {
            const buf = await buffer(req);
            const sig = req.headers['stripe-signature'];

            let event;
            try {
                event = stripe.webhooks.constructEvent(buf, sig, process.env.STRIPE_WEBHOOK_SECRET);
            } catch (err) {
                console.error(`Webhook Error: ${err.message}`);
                return res.status(400).send(`Webhook Error: ${err.message}`);
            }

            // Handle the event
            switch (event.type) {
                case 'checkout.session.completed':
                    const checkoutSessionCompleted = event.data.object;
                    // Fulfill the purchase, e.g., grant access to content
                    console.log('Checkout Session Completed:', checkoutSessionCompleted);
                    break;
                // ... handle other event types
                default:
                    console.log(`Unhandled event type ${event.type}`);
            }

            res.status(200).json({ received: true });
        } else {
            res.setHeader('Allow', 'POST');
            res.status(405).end('Method Not Allowed');
        }
    }
    ```

## 7. Testing

To ensure the Stripe integration is working correctly, perform the following testing steps:

1.  **Stripe Dashboard Setup:**
    *   Ensure you have a Stripe account and are operating in **Test mode**.
    *   Verify that your **Publishable key**, **Secret key**, and **Webhook secret** are correctly set in your `.env.local` file.
    *   Confirm that you have created the necessary **Products** and **Price IDs** in the Stripe Dashboard, matching those configured in your `.env.local`.

2.  **Local Server & Webhook Listener:**
    *   Start your local development server (e.g., `npm run dev`).
    *   If using Stripe webhooks, set up a local webhook listener using the Stripe CLI:
        ```bash
        stripe listen --forward-to localhost:3000/api/webhooks
        ```
        Replace `3000/api/webhooks` with the actual path to your webhook endpoint. This will provide a `whsec_` secret that you should use in your `.env.local`.

3.  **Simulated Payment Flow:**
    *   Navigate to the part of your application that initiates a Stripe checkout (e.g., a "Buy Now" button).
    *   Initiate a payment.
    *   When prompted for credit card details, use Stripe's provided [test card numbers](https://stripe.com/docs/testing#cards) (e.g., `4242 4242 4242 4242` for a successful payment, `4007 0000 0000 2743` for a card declined error).
    *   Complete the payment process.

4.  **Verification:**
    *   **Application UI:** Check if the application's success/failure pages are displayed correctly based on the payment outcome.
    *   **Stripe Dashboard:**
        *   Go to **Payments** in your Stripe Dashboard (in Test mode). Verify that the transaction appears with the correct status (e.g., `succeeded`, `failed`).
        *   If using subscriptions, check the **Subscriptions** section.
    *   **Server Logs (for webhooks):** If you configured webhooks, check your server console and the Stripe CLI listener for incoming webhook events (e.g., `checkout.session.completed`). This confirms that your backend is receiving and processing events from Stripe.

## 8. Migration Guide

**Not Applicable.**

This feature is an addition to the existing codebase and does not introduce any breaking changes or require specific migration steps for existing functionality. For new installations or upgrading existing projects, refer to the "Usage Examples" section for detailed instructions on how to set up and configure the Stripe integration.