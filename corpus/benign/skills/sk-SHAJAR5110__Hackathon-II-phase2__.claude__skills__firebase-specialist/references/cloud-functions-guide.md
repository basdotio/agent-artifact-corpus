# Cloud Functions - Complete Guide

## HTTP Callable Functions

```typescript
// functions/src/http-functions.ts
import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import axios from 'axios';

const db = admin.firestore();

// HTTP Callable function for cart checkout
export const checkoutCart = functions.https.onCall(async (data, context) => {
  // Verify authentication
  if (!context.auth) {
    throw new functions.https.HttpsError(
      'unauthenticated',
      'User must be authenticated'
    );
  }

  const { cartItems, shippingAddress, billingAddress, promoCode } = data;
  const userId = context.auth.uid;

  try {
    // Validate cart items
    let subtotal = 0;
    const batch = db.batch();

    for (const item of cartItems) {
      const productDoc = await db
        .collection('products')
        .doc(item.productId)
        .get();
      if (!productDoc.exists) {
        throw new Error(`Product ${item.productId} not found`);
      }

      const product = productDoc.data();
      if (product.inventory.available < item.quantity) {
        throw new Error(`Insufficient inventory for ${product.name}`);
      }

      subtotal += product.price * item.quantity;

      // Reserve inventory
      batch.update(productDoc.ref, {
        'inventory.reserved': admin.firestore.FieldValue.increment(
          item.quantity
        ),
        'inventory.available': admin.firestore.FieldValue.increment(
          -item.quantity
        ),
      });
    }

    // Apply promo code
    let discount = 0;
    if (promoCode) {
      const promoDoc = await db
        .collection('promos')
        .doc(promoCode)
        .get();
      if (promoDoc.exists && promoDoc.data().isActive) {
        discount = subtotal * (promoDoc.data().discountPercent / 100);
      }
    }

    // Calculate total
    const tax = (subtotal - discount) * 0.1;
    const total = subtotal - discount + tax;

    // Create order
    const orderRef = db.collection('orders').doc();
    batch.set(orderRef, {
      userId,
      orderNumber: `ORD-${Date.now()}`,
      items: cartItems,
      shippingAddress,
      billingAddress,
      pricing: { subtotal, discount, tax, total },
      status: 'pending',
      payment: { status: 'pending' },
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
    });

    await batch.commit();

    return {
      success: true,
      orderId: orderRef.id,
      total,
    };
  } catch (error: any) {
    throw new functions.https.HttpsError(
      'internal',
      error.message || 'Checkout failed'
    );
  }
});

// Callable function for Stripe payment
export const createPaymentIntent = functions.https.onCall(
  async (data, context) => {
    if (!context.auth) {
      throw new functions.https.HttpsError(
        'unauthenticated',
        'User must be authenticated'
      );
    }

    const { orderId, amount } = data;
    const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

    try {
      const paymentIntent = await stripe.paymentIntents.create({
        amount: Math.round(amount * 100),
        currency: 'usd',
        metadata: { orderId, userId: context.auth.uid },
      });

      return {
        success: true,
        clientSecret: paymentIntent.client_secret,
      };
    } catch (error: any) {
      throw new functions.https.HttpsError(
        'internal',
        error.message || 'Payment intent creation failed'
      );
    }
  }
);
```

## Firestore Triggers

```typescript
// functions/src/firestore-triggers.ts

// Trigger when product is created or updated
export const onProductChange = functions.firestore
  .document('products/{productId}')
  .onWrite(async (change, context) => {
    const productId = context.params.productId;
    const newData = change.after.data();

    if (!change.before.exists) {
      // Product created - log event
      console.log('New product created:', productId);
      await db.collection('activity_log').add({
        type: 'product_created',
        productId,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
      });
    } else if (change.after.exists) {
      // Product updated - sync denormalized copies
      const oldData = change.before.data();

      if (newData.price !== oldData.price) {
        // Price changed - update in orders
        const batch = db.batch();
        const ordersSnapshot = await db
          .collectionGroup('items')
          .where('productId', '==', productId)
          .get();

        ordersSnapshot.docs.forEach((doc) => {
          batch.update(doc.ref, { price: newData.price });
        });

        await batch.commit();
      }
    }
  });

// Trigger when order is created
export const onOrderCreated = functions.firestore
  .document('orders/{orderId}')
  .onCreate(async (snap, context) => {
    const order = snap.data();
    const orderId = context.params.orderId;

    try {
      // Send order confirmation email
      const mailFunction = require('./mail');
      await mailFunction.sendOrderConfirmation(order);

      // Update inventory
      const batch = db.batch();
      for (const item of order.items) {
        const productRef = db.collection('products').doc(item.productId);
        batch.update(productRef, {
          'inventory.available': admin.firestore.FieldValue.increment(
            -item.quantity
          ),
        });
      }
      await batch.commit();

      // Create order in analytics
      await db.collection('analytics_orders').add({
        orderId,
        userId: order.userId,
        amount: order.pricing.total,
        currency: 'USD',
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
      });
    } catch (error) {
      console.error('Order creation trigger failed:', error);
    }
  });

// Trigger when payment status changes
export const onPaymentStatusChange = functions.firestore
  .document('payments/{paymentId}')
  .onUpdate(async (change, context) => {
    const newData = change.after.data();
    const oldData = change.before.data();

    if (newData.status === 'completed' && oldData.status !== 'completed') {
      // Payment completed
      const orderId = newData.orderId;
      const orderRef = db.collection('orders').doc(orderId);

      await orderRef.update({
        status: 'confirmed',
        'payment.status': 'completed',
        'payment.completedAt':
          admin.firestore.FieldValue.serverTimestamp(),
      });

      // Send confirmation email
      const orderDoc = await orderRef.get();
      await sendConfirmationEmail(orderDoc.data());
    }
  });

// Cleanup trigger - delete related data
export const onOrderDeleted = functions.firestore
  .document('orders/{orderId}')
  .onDelete(async (snap, context) => {
    const orderId = context.params.orderId;

    const batch = db.batch();

    // Delete related payment records
    const paymentsSnapshot = await db
      .collection('payments')
      .where('orderId', '==', orderId)
      .get();

    paymentsSnapshot.docs.forEach((doc) => {
      batch.delete(doc.ref);
    });

    await batch.commit();
  });
```

## Scheduled Functions

```typescript
// functions/src/scheduled-functions.ts

// Send daily digest emails
export const sendDailyDigest = functions.pubsub
  .schedule('0 9 * * *')
  .timeZone('America/New_York')
  .onRun(async (context) => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    // Get orders from yesterday
    const ordersSnapshot = await db
      .collection('orders')
      .where(
        'createdAt',
        '>=',
        admin.firestore.Timestamp.fromDate(yesterday)
      )
      .get();

    // Get daily stats
    const stats = {
      totalOrders: ordersSnapshot.size,
      totalRevenue: 0,
      averageOrderValue: 0,
    };

    ordersSnapshot.docs.forEach((doc) => {
      stats.totalRevenue += doc.data().pricing.total;
    });

    stats.averageOrderValue =
      stats.totalOrders > 0 ? stats.totalRevenue / stats.totalOrders : 0;

    // Send to admin
    const adminDoc = await db.collection('admins').limit(1).get();
    if (!adminDoc.empty) {
      await sendEmail({
        to: adminDoc.docs[0].data().email,
        subject: 'Daily Sales Digest',
        template: 'daily_digest',
        data: { stats, date: new Date().toISOString() },
      });
    }

    console.log('Daily digest sent with stats:', stats);
  });

// Weekly backup
export const weeklyBackup = functions.pubsub
  .schedule('0 2 ? * SUN')
  .timeZone('UTC')
  .onRun(async (context) => {
    const backup = require('@google-cloud/firestore').Firestore;
    console.log('Weekly backup initiated');
    // Implement backup logic
  });

// Cleanup old cart records
export const cleanupOldCarts = functions.pubsub
  .schedule('0 1 * * *')
  .timeZone('UTC')
  .onRun(async (context) => {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const snapshot = await db
      .collection('carts')
      .where(
        'lastModified',
        '<',
        admin.firestore.Timestamp.fromDate(thirtyDaysAgo)
      )
      .get();

    const batch = db.batch();
    snapshot.docs.forEach((doc) => {
      batch.delete(doc.ref);
    });

    await batch.commit();
    console.log(`Deleted ${snapshot.size} old carts`);
  });
```

## Error Handling & Retry Logic

```typescript
// functions/src/error-handling.ts

interface RetryConfig {
  maxRetries: number;
  backoffMs: number;
  backoffMultiplier: number;
}

async function retryFunction<T>(
  fn: () => Promise<T>,
  config: RetryConfig = {
    maxRetries: 3,
    backoffMs: 1000,
    backoffMultiplier: 2,
  }
): Promise<T> {
  let lastError: any;
  let delay = config.backoffMs;

  for (let i = 0; i <= config.maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      // Don't retry on auth errors
      if (error.code === 'PERMISSION_DENIED') {
        throw error;
      }

      if (i < config.maxRetries) {
        console.log(`Retry ${i + 1}/${config.maxRetries} after ${delay}ms`);
        await new Promise((resolve) => setTimeout(resolve, delay));
        delay *= config.backoffMultiplier;
      }
    }
  }

  throw lastError;
}

// Example usage in Cloud Function
export const resilientPaymentProcessing = functions.https.onCall(
  async (data, context) => {
    return retryFunction(
      async () => {
        return processPayment(data);
      },
      { maxRetries: 3, backoffMs: 2000, backoffMultiplier: 2 }
    );
  }
);

// Error logging
export async function logError(
  error: any,
  context: { functionName?: string; data?: any }
) {
  await db.collection('errors').add({
    message: error.message,
    stack: error.stack,
    context,
    timestamp: admin.firestore.FieldValue.serverTimestamp(),
    severity: 'error',
  });
}

// Send error alert
export async function alertOnError(error: any) {
  const alertsCollection = await db.collection('settings').doc('alerts').get();
  if (!alertsCollection.exists) return;

  const { email: adminEmail } = alertsCollection.data() || {};
  if (adminEmail) {
    await sendEmail({
      to: adminEmail,
      subject: 'Firebase Function Error Alert',
      template: 'error_alert',
      data: { error: error.message, timestamp: new Date() },
    });
  }
}
```

## Third-Party Integration

```typescript
// Webhook handling for Stripe
export const handleStripeWebhook = functions.https.onRequest(
  async (req, res) => {
    const sig = req.headers['stripe-signature'] as string;
    const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

    let event;

    try {
      event = stripe.webhooks.constructEvent(
        req.rawBody,
        sig,
        process.env.STRIPE_WEBHOOK_SECRET
      );
    } catch (error: any) {
      res.status(400).send(`Webhook Error: ${error.message}`);
      return;
    }

    try {
      switch (event.type) {
        case 'payment_intent.succeeded':
          await handlePaymentSuccess(event.data.object);
          break;
        case 'payment_intent.payment_failed':
          await handlePaymentFailure(event.data.object);
          break;
        case 'invoice.payment_succeeded':
          await handleInvoicePayment(event.data.object);
          break;
      }

      res.json({ received: true });
    } catch (error) {
      console.error('Webhook processing error:', error);
      res.status(500).send('Webhook processing failed');
    }
  }
);

async function handlePaymentSuccess(paymentIntent: any) {
  const { orderId, userId } = paymentIntent.metadata;

  await db.collection('orders').doc(orderId).update({
    status: 'confirmed',
    'payment.status': 'completed',
    'payment.stripePaymentIntentId': paymentIntent.id,
  });

  // Send confirmation email
  const orderDoc = await db.collection('orders').doc(orderId).get();
  console.log('Payment succeeded for order:', orderId);
}

async function handlePaymentFailure(paymentIntent: any) {
  const { orderId } = paymentIntent.metadata;

  await db.collection('orders').doc(orderId).update({
    'payment.status': 'failed',
    'payment.errorMessage': paymentIntent.last_payment_error?.message,
  });

  console.log('Payment failed for order:', orderId);
}
```

## Best Practices

**Performance:**
- Keep functions under 15 seconds execution
- Use batch operations for multiple writes
- Cache data in memory when possible
- Clean up resources properly

**Security:**
- Always verify authentication context
- Validate all inputs
- Use environment variables for secrets
- Implement rate limiting
- Log security-relevant events

**Reliability:**
- Implement retry logic
- Handle timeouts gracefully
- Log errors comprehensively
- Monitor function performance
- Test error scenarios