# Payment Integration - Stripe, JazzCash, EasyPaisa

## Stripe Integration

### Complete Stripe Setup

```typescript
// services/stripe.service.ts
import Stripe from 'stripe';
import {
  getFunctions,
  httpsCallable,
} from 'firebase/functions';

const stripe = new Stripe(process.env.REACT_APP_STRIPE_KEY || '');

interface PaymentIntent {
  clientSecret: string;
  amount: number;
  currency: string;
}

export const stripeService = {
  // Create payment intent
  async createPaymentIntent(
    orderId: string,
    amount: number,
    currency: string = 'usd'
  ): Promise<PaymentIntent> {
    const functions = getFunctions();
    const createIntent = httpsCallable(
      functions,
      'createPaymentIntent'
    );

    const response = await createIntent({
      orderId,
      amount,
      currency,
    });

    return response.data as PaymentIntent;
  },

  // Confirm card payment
  async confirmCardPayment(
    clientSecret: string,
    cardElement: any
  ): Promise<{ success: boolean; paymentIntentId?: string; error?: string }> {
    try {
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: cardElement,
          billing_details: {
            name: 'Customer',
          },
        },
      });

      if (result.error) {
        return { success: false, error: result.error.message };
      }

      return {
        success: true,
        paymentIntentId: result.paymentIntent.id,
      };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  },

  // Create subscription
  async createSubscription(
    customerId: string,
    priceId: string
  ): Promise<{ subscriptionId: string; clientSecret: string }> {
    const functions = getFunctions();
    const createSub = httpsCallable(functions, 'createSubscription');

    const response = await createSub({
      customerId,
      priceId,
    });

    return response.data;
  },

  // Cancel subscription
  async cancelSubscription(
    subscriptionId: string
  ): Promise<{ success: boolean }> {
    const functions = getFunctions();
    const cancelSub = httpsCallable(functions, 'cancelSubscription');

    await cancelSub({ subscriptionId });
    return { success: true };
  },

  // Get customer
  async getCustomer(customerId: string) {
    const functions = getFunctions();
    const getCustomerFn = httpsCallable(functions, 'getCustomer');

    const response = await getCustomerFn({ customerId });
    return response.data;
  },

  // List payment methods
  async listPaymentMethods(customerId: string) {
    const functions = getFunctions();
    const listMethods = httpsCallable(functions, 'listPaymentMethods');

    const response = await listMethods({ customerId });
    return response.data;
  },
};

// Cloud Function for Stripe
export const createPaymentIntentFunction = functions.https.onCall(
  async (data, context) => {
    if (!context.auth) {
      throw new functions.https.HttpsError(
        'unauthenticated',
        'User must be authenticated'
      );
    }

    const { orderId, amount, currency = 'usd' } = data;
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');

    try {
      const paymentIntent = await stripe.paymentIntents.create({
        amount: Math.round(amount * 100),
        currency,
        metadata: {
          orderId,
          userId: context.auth.uid,
        },
      });

      // Store in Firestore
      await db.collection('payments').add({
        userId: context.auth.uid,
        orderId,
        stripePaymentIntentId: paymentIntent.id,
        amount,
        currency,
        status: 'created',
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      return {
        clientSecret: paymentIntent.client_secret,
        amount,
        currency,
      };
    } catch (error: any) {
      throw new functions.https.HttpsError(
        'internal',
        error.message || 'Failed to create payment intent'
      );
    }
  }
);
```

## JazzCash Integration (Pakistan)

### JazzCash Payment Flow

```typescript
// services/jazzcash.service.ts
import crypto from 'crypto';

interface JazzCashConfig {
  merchantId: string;
  password: string;
  apiUsername: string;
  apiPassword: string;
  ppApiUrl: string;
}

export class JazzCashService {
  private config: JazzCashConfig;

  constructor(config: JazzCashConfig) {
    this.config = config;
  }

  // Generate secure hash
  private generateHash(
    data: Record<string, string>
  ): string {
    const sortedData = Object.keys(data)
      .sort()
      .map(key => `${key}=${data[key]}`)
      .join('&');

    return crypto
      .createHash('sha256')
      .update(
        sortedData + '&' + this.config.password
      )
      .digest('hex');
  }

  // Initialize payment
  async initializePayment(params: {
    amount: number;
    orderId: string;
    email: string;
    phone: string;
    description: string;
  }): Promise<{ paymentUrl: string; referenceId: string }> {
    const referenceId = `ORD${params.orderId}${Date.now()}`;

    const paymentData = {
      pp_Version: '1.1',
      pp_TxnType: 'MPAY',
      pp_Language: 'EN',
      pp_MerchantID: this.config.merchantId,
      pp_SubMerchantID: '',
      pp_Password: this.config.password,
      pp_BankID: '',
      pp_ProductID: '',
      pp_TxnRefNo: referenceId,
      pp_Amount: (params.amount * 100).toString(), // In paisas
      pp_TxnCurrency: 'PKR',
      pp_TxnDateTime: new Date().toISOString().slice(0, 19),
      pp_BillReference: params.orderId,
      pp_Description: params.description,
      pp_SecureHash: '',
    };

    paymentData.pp_SecureHash = this.generateHash(paymentData);

    return {
      paymentUrl: `${this.config.ppApiUrl}?${new URLSearchParams(paymentData).toString()}`,
      referenceId,
    };
  }

  // Handle callback
  handleCallback(callbackData: Record<string, string>): {
    success: boolean;
    referenceId?: string;
    responseCode?: string;
    message?: string;
  } {
    // Verify signature
    const receivedHash = callbackData.pp_SecureHash;
    delete callbackData.pp_SecureHash;

    const calculatedHash = this.generateHash(callbackData);

    if (receivedHash !== calculatedHash) {
      return {
        success: false,
        message: 'Invalid signature',
      };
    }

    const responseCode = callbackData.pp_ResponseCode;
    const isSuccess = responseCode === '0';

    return {
      success: isSuccess,
      referenceId: callbackData.pp_TxnRefNo,
      responseCode,
      message: callbackData.pp_ResponseMessage,
    };
  }

  // Check transaction status
  async checkTransactionStatus(
    referenceId: string
  ): Promise<{
    status: string;
    responseCode: string;
  }> {
    const params = {
      pp_MerchantID: this.config.merchantId,
      pp_Password: this.config.password,
      pp_TxnRefNo: referenceId,
      pp_ApiUsername: this.config.apiUsername,
      pp_ApiPassword: this.config.apiPassword,
    };

    const hash = this.generateHash(params);
    params['pp_SecureHash'] = hash;

    try {
      const response = await fetch(
        `${this.config.ppApiUrl}CheckTransactionStatus`,
        {
          method: 'POST',
          body: new URLSearchParams(params),
        }
      );

      const data = await response.json();
      return {
        status: data.pp_TxnStatus,
        responseCode: data.pp_ResponseCode,
      };
    } catch (error) {
      throw new Error('Failed to check transaction status');
    }
  }
}

// Cloud Function to handle JazzCash callback
export const handleJazzCashCallback = functions.https.onRequest(
  async (req, res) => {
    try {
      const jazzCash = new JazzCashService({
        merchantId: process.env.JAZZCASH_MERCHANT_ID || '',
        password: process.env.JAZZCASH_PASSWORD || '',
        apiUsername: process.env.JAZZCASH_API_USERNAME || '',
        apiPassword: process.env.JAZZCASH_API_PASSWORD || '',
        ppApiUrl: process.env.JAZZCASH_API_URL || '',
      });

      const callbackResult = jazzCash.handleCallback(req.query);

      if (!callbackResult.success) {
        return res.status(400).json({
          success: false,
          message: callbackResult.message,
        });
      }

      // Extract order ID from reference
      const orderIdMatch = callbackResult.referenceId?.match(
        /ORD(\w+)/
      );
      if (!orderIdMatch) {
        throw new Error('Invalid reference ID');
      }

      const orderId = orderIdMatch[1];

      // Update payment in Firestore
      const paymentSnapshot = await db
        .collection('payments')
        .where('jazzCashReferenceId', '==', callbackResult.referenceId)
        .get();

      if (!paymentSnapshot.empty) {
        await paymentSnapshot.docs[0].ref.update({
          status: 'completed',
          responseCode: callbackResult.responseCode,
          completedAt:
            admin.firestore.FieldValue.serverTimestamp(),
        });

        // Update order
        await db.collection('orders').doc(orderId).update({
          status: 'confirmed',
          'payment.status': 'completed',
        });
      }

      res.json({ success: true });
    } catch (error: any) {
      console.error('JazzCash callback error:', error);
      res.status(500).json({ success: false, error: error.message });
    }
  }
);
```

## EasyPaisa Integration (Pakistan)

### EasyPaisa Payment Flow

```typescript
// services/easypaisa.service.ts
interface EasyPaisaConfig {
  storeId: string;
  password: string;
  apiUrl: string;
}

export class EasyPaisaService {
  private config: EasyPaisaConfig;

  constructor(config: EasyPaisaConfig) {
    this.config = config;
  }

  // Create transaction request
  async initiatePayment(params: {
    amount: number;
    orderId: string;
    customerEmail: string;
    customerPhone: string;
    description: string;
  }): Promise<{
    transactionId: string;
    token: string;
    paymentUrl: string;
  }> {
    const transactionId = `TXN${params.orderId}${Date.now()}`;

    const requestData = {
      StoreId: this.config.storeId,
      AuthToken: this.generateToken(),
      TransactionId: transactionId,
      Amount: params.amount.toString(),
      CustomerEmail: params.customerEmail,
      CustomerPhone: params.customerPhone,
      Description: params.description,
      TransactionType: 'DirectLoad',
    };

    try {
      const response = await fetch(`${this.config.apiUrl}/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
      });

      const data = await response.json();

      if (!data.Success) {
        throw new Error(data.Message);
      }

      return {
        transactionId,
        token: data.Token,
        paymentUrl: `${this.config.apiUrl}/pay?token=${data.Token}`,
      };
    } catch (error: any) {
      throw new Error(`EasyPaisa initiation failed: ${error.message}`);
    }
  }

  // Verify payment
  async verifyPayment(transactionId: string): Promise<{
    success: boolean;
    status: string;
    message?: string;
  }> {
    const verifyData = {
      StoreId: this.config.storeId,
      AuthToken: this.generateToken(),
      TransactionId: transactionId,
    };

    try {
      const response = await fetch(`${this.config.apiUrl}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(verifyData),
      });

      const data = await response.json();

      return {
        success: data.Success,
        status: data.Status,
        message: data.Message,
      };
    } catch (error: any) {
      throw new Error(`EasyPaisa verification failed: ${error.message}`);
    }
  }

  // Generate auth token
  private generateToken(): string {
    const timestamp = Date.now().toString();
    return btoa(`${this.config.storeId}:${this.config.password}:${timestamp}`);
  }
}

// Cloud Function to handle EasyPaisa callback
export const handleEasyPaisaCallback = functions.https.onRequest(
  async (req, res) => {
    try {
      const easyPaisa = new EasyPaisaService({
        storeId: process.env.EASYPAISA_STORE_ID || '',
        password: process.env.EASYPAISA_PASSWORD || '',
        apiUrl: process.env.EASYPAISA_API_URL || '',
      });

      const { transactionId, status } = req.body;

      // Verify payment
      const verification = await easyPaisa.verifyPayment(transactionId);

      if (!verification.success) {
        return res.status(400).json({
          success: false,
          message: verification.message,
        });
      }

      // Update payment record
      const paymentSnapshot = await db
        .collection('payments')
        .where('easyPaisaTransactionId', '==', transactionId)
        .get();

      if (!paymentSnapshot.empty) {
        const paymentDoc = paymentSnapshot.docs[0];
        const orderId = paymentDoc.data().orderId;

        await paymentDoc.ref.update({
          status: 'completed',
          verifiedAt: admin.firestore.FieldValue.serverTimestamp(),
        });

        // Update order
        await db.collection('orders').doc(orderId).update({
          status: 'confirmed',
          'payment.status': 'completed',
        });
      }

      res.json({ success: true });
    } catch (error: any) {
      console.error('EasyPaisa callback error:', error);
      res.status(500).json({ success: false, error: error.message });
    }
  }
);
```

## Subscription Management

```typescript
// services/subscription.service.ts

export const subscriptionService = {
  // Create subscription
  async createSubscription(
    customerId: string,
    planId: string
  ): Promise<string> {
    const functions = getFunctions();
    const createSub = httpsCallable(functions, 'createSubscription');

    const response = await createSub({
      customerId,
      planId,
    });

    return response.data.subscriptionId;
  },

  // Update subscription
  async updateSubscription(
    subscriptionId: string,
    planId: string
  ): Promise<boolean> {
    const functions = getFunctions();
    const updateSub = httpsCallable(functions, 'updateSubscription');

    await updateSub({ subscriptionId, planId });
    return true;
  },

  // Cancel subscription
  async cancelSubscription(subscriptionId: string): Promise<boolean> {
    const functions = getFunctions();
    const cancelSub = httpsCallable(functions, 'cancelSubscription');

    await cancelSub({ subscriptionId });
    return true;
  },

  // Get subscription details
  async getSubscription(subscriptionId: string) {
    const functions = getFunctions();
    const getSub = httpsCallable(functions, 'getSubscription');

    const response = await getSub({ subscriptionId });
    return response.data;
  },

  // Handle subscription webhook
  async handleSubscriptionWebhook(
    event: Record<string, any>
  ): Promise<void> {
    const { type, data } = event;

    switch (type) {
      case 'customer.subscription.updated':
        await updateSubscriptionRecord(data.object);
        break;
      case 'customer.subscription.deleted':
        await cancelSubscriptionRecord(data.object.id);
        break;
      case 'invoice.payment_succeeded':
        await recordSubscriptionPayment(data.object);
        break;
      case 'invoice.payment_failed':
        await handleFailedPayment(data.object);
        break;
    }
  },
};
```

## Refund Processing

```typescript
// Cloud Function for refunds
export const processRefund = functions.https.onCall(
  async (data, context) => {
    if (!context.auth) {
      throw new functions.https.HttpsError(
        'unauthenticated',
        'User must be authenticated'
      );
    }

    const { paymentId, reason, amount } = data;
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');

    try {
      const paymentDoc = await db
        .collection('payments')
        .doc(paymentId)
        .get();

      if (!paymentDoc.exists) {
        throw new Error('Payment not found');
      }

      const payment = paymentDoc.data();

      // Create refund in Stripe
      const refund = await stripe.refunds.create({
        payment_intent: payment.stripePaymentIntentId,
        amount: amount ? Math.round(amount * 100) : undefined,
        reason: reason || 'requested_by_customer',
      });

      // Update payment record
      await paymentDoc.ref.update({
        status: 'refunded',
        refundId: refund.id,
        refundAmount: refund.amount / 100,
        refundReason: reason,
        refundedAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      // Update order status
      const orderId = payment.orderId;
      await db.collection('orders').doc(orderId).update({
        status: 'refunded',
      });

      return { success: true, refundId: refund.id };
    } catch (error: any) {
      throw new functions.https.HttpsError(
        'internal',
        error.message || 'Refund processing failed'
      );
    }
  }
);
```

## Invoice Generation

```typescript
// services/invoice.service.ts
import { PDFDocument, rgb } from 'pdf-lib';

export const invoiceService = {
  async generateInvoice(orderId: string): Promise<Buffer> {
    const orderDoc = await db.collection('orders').doc(orderId).get();
    const order = orderDoc.data();

    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage([600, 800]);

    // Add header
    page.drawText(`Invoice #${order.orderNumber}`, {
      x: 50,
      y: 750,
      size: 24,
      color: rgb(0, 0, 0),
    });

    // Add order details
    page.drawText(`Order Date: ${order.createdAt.toDate()}`, {
      x: 50,
      y: 700,
      size: 12,
    });

    // Add items
    let yPosition = 650;
    order.items.forEach((item: any) => {
      page.drawText(`${item.productName} x${item.quantity}: $${item.price * item.quantity}`, {
        x: 50,
        y: yPosition,
        size: 11,
      });
      yPosition -= 20;
    });

    // Add totals
    page.drawText(`Subtotal: $${order.pricing.subtotal}`, {
      x: 50,
      y: yPosition - 20,
      size: 12,
      color: rgb(0, 0, 0),
    });

    page.drawText(`Total: $${order.pricing.total}`, {
      x: 50,
      y: yPosition - 40,
      size: 14,
      color: rgb(0, 0, 0),
    });

    const pdfBytes = await pdfDoc.save();
    return Buffer.from(pdfBytes);
  },
};
```