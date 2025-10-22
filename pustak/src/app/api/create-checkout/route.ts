import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { plan, userId, userEmail } = body;
    
    if (!plan || !userId || !userEmail) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }
    
    // Call backend to create Stripe checkout session
    const response = await fetch(`${BACKEND_URL}/stripe/create-checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        user_email: userEmail,
        plan: plan,
        success_url: `${request.nextUrl.origin}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${request.nextUrl.origin}/pricing`,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to create checkout session');
    }
    
    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Checkout error:', error);
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    );
  }
}
