# Forms, Validation & Payment Integration

## Advanced Form Handling with react-hook-form + Zod

### Multi-Step Checkout Form

```typescript
// components/checkout/CheckoutForm.tsx
'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCartStore } from '@/store/cartStore';
import { useAuthStore } from '@/store/authStore';
import toast from 'react-hot-toast';

// Step 1: Shipping Info
const shippingSchema = z.object({
  fullName: z.string().min(2, 'Name required'),
  email: z.string().email('Invalid email'),
  phone: z.string().min(10, 'Invalid phone'),
  address: z.string().min(5, 'Address required'),
  city: z.string().min(2, 'City required'),
  state: z.string().min(2, 'State required'),
  postalCode: z.string().min(3, 'Postal code required'),
  country: z.string().min(2, 'Country required'),
});

// Step 2: Billing Info
const billingSchema = z.object({
  isSameAsShipping: z.boolean(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  postalCode: z.string().optional(),
  country: z.string().optional(),
}).refine(
  (data) => {
    if (!data.isSameAsShipping) {
      return data.address && data.city && data.state && data.postalCode && data.country;
    }
    return true;
  },
  { message: 'Billing address required', path: ['address'] }
);

// Step 3: Payment Method
const paymentSchema = z.object({
  method: z.enum(['stripe', 'jazzcash', 'easypaisa']),
});

type ShippingInput = z.infer<typeof shippingSchema>;
type BillingInput = z.infer<typeof billingSchema>;
type PaymentInput = z.infer<typeof paymentSchema>;

export function CheckoutForm() {
  const [step, setStep] = useState<'shipping' | 'billing' | 'payment' | 'review'>(
    'shipping'
  );
  const [shippingData, setShippingData] = useState<ShippingInput | null>(null);
  const [billingData, setBillingData] = useState<BillingInput | null>(null);
  const [paymentData, setPaymentData] = useState<PaymentInput | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const cart = useCartStore();
  const user = useAuthStore(state => state.user);

  // Shipping Form
  const shippingForm = useForm<ShippingInput>({
    resolver: zodResolver(shippingSchema),
  });

  const onShippingSubmit = async (data: ShippingInput) => {
    setShippingData(data);
    setStep('billing');
  };

  // Billing Form
  const billingForm = useForm<BillingInput>({
    resolver: zodResolver(billingSchema),
  });

  const onBillingSubmit = async (data: BillingInput) => {
    setBillingData(data);
    setStep('payment');
  };

  // Payment Form
  const paymentForm = useForm<PaymentInput>({
    resolver: zodResolver(paymentSchema),
  });

  const onPaymentSubmit = async (data: PaymentInput) => {
    setPaymentData(data);
    setStep('review');
  };

  // Process Order
  const handlePlaceOrder = async () => {
    if (!shippingData || !paymentData || !user) {
      toast.error('Missing required information');
      return;
    }

    setIsProcessing(true);
    try {
      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: user.uid,
          items: cart.items,
          shipping: shippingData,
          billing: billingData || shippingData,
          paymentMethod: paymentData.method,
        }),
      });

      if (!response.ok) throw new Error('Order creation failed');

      const order = await response.json();
      
      // Process payment based on method
      if (paymentData.method === 'stripe') {
        const checkoutResponse = await fetch('/api/checkout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            orderId: order.id,
            items: cart.items,
            amount: cart.getTotal(),
          }),
        });

        const checkoutData = await checkoutResponse.json();
        // Redirect to Stripe checkout
        window.location.href = checkoutData.checkoutUrl;
      } else {
        toast.success('Order placed successfully!');
        cart.clearCart();
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to place order');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Step Indicators */}
      <div className="flex gap-4 mb-8">
        {(['shipping', 'billing', 'payment', 'review'] as const).map((s, i) => (
          <div
            key={s}
            className={`flex items-center gap-2 ${
              ['shipping', 'billing', 'payment', 'review'].indexOf(step) >= i
                ? 'text-blue-600'
                : 'text-gray-400'
            }`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center ${
                ['shipping', 'billing', 'payment', 'review'].indexOf(step) >= i
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200'
              }`}
            >
              {i + 1}
            </div>
            <span className="hidden sm:inline capitalize">{s}</span>
          </div>
        ))}
      </div>

      {/* Shipping Step */}
      {step === 'shipping' && (
        <form onSubmit={shippingForm.handleSubmit(onShippingSubmit)} className="space-y-4">
          <h2 className="text-2xl font-bold mb-4">Shipping Information</h2>
          
          <input
            {...shippingForm.register('fullName')}
            placeholder="Full Name"
            className="w-full px-4 py-2 border rounded-lg"
          />
          {shippingForm.formState.errors.fullName && (
            <p className="text-red-500 text-sm">
              {shippingForm.formState.errors.fullName.message}
            </p>
          )}

          <input
            {...shippingForm.register('email')}
            placeholder="Email"
            type="email"
            className="w-full px-4 py-2 border rounded-lg"
          />

          <input
            {...shippingForm.register('phone')}
            placeholder="Phone"
            className="w-full px-4 py-2 border rounded-lg"
          />

          <textarea
            {...shippingForm.register('address')}
            placeholder="Address"
            className="w-full px-4 py-2 border rounded-lg"
          />

          <div className="grid grid-cols-2 gap-4">
            <input
              {...shippingForm.register('city')}
              placeholder="City"
              className="px-4 py-2 border rounded-lg"
            />
            <input
              {...shippingForm.register('state')}
              placeholder="State"
              className="px-4 py-2 border rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <input
              {...shippingForm.register('postalCode')}
              placeholder="Postal Code"
              className="px-4 py-2 border rounded-lg"
            />
            <input
              {...shippingForm.register('country')}
              placeholder="Country"
              className="px-4 py-2 border rounded-lg"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700"
          >
            Continue to Billing
          </button>
        </form>
      )}

      {/* Billing Step */}
      {step === 'billing' && (
        <form onSubmit={billingForm.handleSubmit(onBillingSubmit)} className="space-y-4">
          <h2 className="text-2xl font-bold mb-4">Billing Information</h2>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              {...billingForm.register('isSameAsShipping')}
              className="w-4 h-4"
            />
            <span>Same as shipping address</span>
          </label>

          {!billingForm.watch('isSameAsShipping') && (
            <>
              <textarea
                {...billingForm.register('address')}
                placeholder="Address"
                className="w-full px-4 py-2 border rounded-lg"
              />
              <div className="grid grid-cols-2 gap-4">
                <input
                  {...billingForm.register('city')}
                  placeholder="City"
                  className="px-4 py-2 border rounded-lg"
                />
                <input
                  {...billingForm.register('state')}
                  placeholder="State"
                  className="px-4 py-2 border rounded-lg"
                />
              </div>
            </>
          )}

          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setStep('shipping')}
              className="flex-1 bg-gray-200 text-gray-900 py-2 rounded-lg font-semibold"
            >
              Back
            </button>
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700"
            >
              Continue to Payment
            </button>
          </div>
        </form>
      )}

      {/* Payment Step */}
      {step === 'payment' && (
        <form onSubmit={paymentForm.handleSubmit(onPaymentSubmit)} className="space-y-4">
          <h2 className="text-2xl font-bold mb-4">Payment Method</h2>

          <div className="space-y-2">
            <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer">
              <input
                type="radio"
                value="stripe"
                {...paymentForm.register('method')}
              />
              <span>Stripe (Credit/Debit Card)</span>
            </label>
            <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer">
              <input
                type="radio"
                value="jazzcash"
                {...paymentForm.register('method')}
              />
              <span>JazzCash (Pakistan)</span>
            </label>
            <label className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer">
              <input
                type="radio"
                value="easypaisa"
                {...paymentForm.register('method')}
              />
              <span>EasyPaisa (Pakistan)</span>
            </label>
          </div>

          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setStep('billing')}
              className="flex-1 bg-gray-200 text-gray-900 py-2 rounded-lg font-semibold"
            >
              Back
            </button>
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700"
            >
              Review Order
            </button>
          </div>
        </form>
      )}

      {/* Review Step */}
      {step === 'review' && (
        <div className="space-y-6">
          <h2 className="text-2xl font-bold">Order Review</h2>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-semibold mb-2">Shipping Address</h3>
            {shippingData && (
              <p className="text-sm text-gray-600">
                {shippingData.address}, {shippingData.city}, {shippingData.state}{' '}
                {shippingData.postalCode}, {shippingData.country}
              </p>
            )}
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-semibold mb-2">Order Summary</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Subtotal:</span>
                <span>${cart.getSubtotal().toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping:</span>
                <span>$10.00</span>
              </div>
              <div className="border-t pt-2 font-semibold flex justify-between">
                <span>Total:</span>
                <span>${cart.getTotal().toFixed(2)}</span>
              </div>
            </div>
          </div>

          <button
            onClick={handlePlaceOrder}
            disabled={isProcessing}
            className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50"
          >
            {isProcessing ? 'Processing...' : 'Place Order'}
          </button>
        </div>
      )}
    </div>
  );
}
```

## Stripe Payment Implementation

```typescript
// lib/stripe.ts
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
  apiVersion: '2023-10-16',
});

export async function createPaymentIntent(
  amount: number,
  currency: string = 'usd',
  metadata?: Record<string, string>
) {
  return stripe.paymentIntents.create({
    amount: Math.round(amount * 100),
    currency,
    metadata,
  });
}

export async function createCheckoutSession(
  lineItems: Stripe.Checkout.SessionCreateParams.LineItem[],
  successUrl: string,
  cancelUrl: string
) {
  return stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: lineItems,
    mode: 'payment',
    success_url: successUrl,
    cancel_url: cancelUrl,
  });
}

export async function createSubscription(
  customerId: string,
  priceId: string
) {
  return stripe.subscriptions.create({
    customer: customerId,
    items: [{ price: priceId }],
    payment_behavior: 'default_incomplete',
    expand: ['latest_invoice.payment_intent'],
  });
}

export async function handleWebhook(
  body: string,
  signature: string
) {
  return stripe.webhooks.constructEvent(
    body,
    signature,
    process.env.STRIPE_WEBHOOK_SECRET || ''
  );
}
```

```typescript
// components/payment/StripePaymentForm.tsx
'use client';

import { useState } from 'react';
import {
  CardElement,
  useStripe,
  useElements,
  Elements,
} from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/js';
import toast from 'react-hot-toast';

const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || ''
);

export function StripePaymentForm({ clientSecret }: { clientSecret: string }) {
  const stripe = useStripe();
  const elements = useElements();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) return;

    setIsLoading(true);
    try {
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: elements.getElement(CardElement)!,
          billing_details: {
            name: 'Customer',
          },
        },
      });

      if (result.error) {
        toast.error(result.error.message);
      } else if (result.paymentIntent?.status === 'succeeded') {
        toast.success('Payment successful!');
        // Redirect to success page
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="p-4 border rounded-lg">
        <CardElement
          options={{
            style: {
              base: {
                fontSize: '16px',
                color: '#424770',
              },
            },
          }}
        />
      </div>

      <button
        type="submit"
        disabled={!stripe || isLoading}
        className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
      >
        {isLoading ? 'Processing...' : 'Pay Now'}
      </button>
    </form>
  );
}

// Wrap with Elements provider
export function StripeProvider({ children }: { children: React.ReactNode }) {
  return (
    <Elements stripe={stripePromise}>
      {children}
    </Elements>
  );
}
```

## JazzCash Payment Implementation

```typescript
// lib/jazzcash.ts
import crypto from 'crypto';

export class JazzCashPayment {
  private merchantId: string;
  private password: string;
  private apiUrl: string;

  constructor() {
    this.merchantId = process.env.JAZZCASH_MERCHANT_ID || '';
    this.password = process.env.JAZZCASH_PASSWORD || '';
    this.apiUrl = process.env.JAZZCASH_API_URL || '';
  }

  private generateHash(data: Record<string, string>): string {
    const sortedData = Object.keys(data)
      .sort()
      .map(key => `${key}=${data[key]}`)
      .join('&');

    return crypto
      .createHash('sha256')
      .update(sortedData + '&' + this.password)
      .digest('hex');
  }

  async initiatePayment(
    orderId: string,
    amount: number,
    email: string,
    phone: string
  ) {
    const transactionId = `ORD${orderId}${Date.now()}`;
    
    const paymentData: Record<string, string> = {
      pp_Version: '1.1',
      pp_TxnType: 'MPAY',
      pp_Language: 'EN',
      pp_MerchantID: this.merchantId,
      pp_Password: this.password,
      pp_TxnRefNo: transactionId,
      pp_Amount: (amount * 100).toString(),
      pp_TxnCurrency: 'PKR',
      pp_TxnDateTime: new Date().toISOString().slice(0, 19),
      pp_BillReference: orderId,
      pp_Description: 'Order Payment',
    };

    paymentData.pp_SecureHash = this.generateHash(paymentData);

    return {
      paymentUrl: `${this.apiUrl}?${new URLSearchParams(paymentData).toString()}`,
      transactionId,
    };
  }

  handleCallback(callbackData: Record<string, string>): {
    success: boolean;
    transactionId?: string;
    error?: string;
  } {
    const receivedHash = callbackData.pp_SecureHash;
    delete callbackData.pp_SecureHash;

    const calculatedHash = this.generateHash(callbackData);

    if (receivedHash !== calculatedHash) {
      return { success: false, error: 'Invalid signature' };
    }

    return {
      success: callbackData.pp_ResponseCode === '0',
      transactionId: callbackData.pp_TxnRefNo,
    };
  }
}
```

This guide covers production-ready form handling, validation, and payment integration patterns!