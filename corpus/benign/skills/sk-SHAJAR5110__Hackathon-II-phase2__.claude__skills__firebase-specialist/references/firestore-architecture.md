# Firestore Database Architecture & Design

## Collection Structure Design

### E-Commerce Database Structure

```typescript
// Complete e-commerce Firestore structure with TypeScript

// ============== USERS COLLECTION ==============
interface UserProfile {
  id: string;
  email: string;
  displayName: string;
  photoURL?: string;
  phone?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
  lastLogin?: Timestamp;
  isActive: boolean;
  role: 'customer' | 'vendor' | 'admin';
  metadata: {
    totalOrders: number;
    totalSpent: number;
    averageRating: number;
  };
}

// ============== PRODUCTS COLLECTION ==============
interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  originalPrice?: number;
  currency: 'USD' | 'PKR' | 'INR';
  inventory: {
    total: number;
    reserved: number;
    available: number;
  };
  images: string[]; // Storage paths
  rating: number;
  reviewCount: number;
  vendorId: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
  isActive: boolean;
  tags: string[];
  seo: {
    slug: string;
    metaDescription: string;
    keywords: string[];
  };
}

// ============== ORDERS COLLECTION ==============
interface Order {
  id: string;
  userId: string;
  orderNumber: string;
  status: 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled' | 'refunded';
  items: OrderItem[];
  shipping: {
    address: Address;
    method: string;
    cost: number;
    estimatedDays: number;
    trackingNumber?: string;
  };
  billing: {
    address: Address;
    method: 'card' | 'mobile' | 'wallet';
  };
  pricing: {
    subtotal: number;
    tax: number;
    shippingCost: number;
    discount: number;
    total: number;
    currency: string;
  };
  payment: {
    status: 'pending' | 'completed' | 'failed' | 'refunded';
    stripePaymentIntentId?: string;
    jazzCashReferenceId?: string;
    transactionId: string;
  };
  notes?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  price: number;
  image: string;
}

interface Address {
  street: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
  fullName: string;
  phone: string;
  isDefault?: boolean;
}

// ============== CART COLLECTION ==============
interface Cart {
  id: string;
  userId: string;
  items: CartItem[];
  lastModified: Timestamp;
  expiresAt: Timestamp;
}

interface CartItem {
  productId: string;
  productName: string;
  quantity: number;
  price: number;
  image: string;
  addedAt: Timestamp;
}

// ============== REVIEWS SUBCOLLECTION ==============
interface Review {
  id: string;
  userId: string;
  userName: string;
  rating: number; // 1-5
  title: string;
  content: string;
  images?: string[];
  helpful: number;
  unhelpful: number;
  verified: boolean;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

// ============== CATEGORIES COLLECTION ==============
interface Category {
  id: string;
  name: string;
  slug: string;
  description: string;
  image?: string;
  parentId?: string;
  sortOrder: number;
  isActive: boolean;
  productCount: number;
}

// ============== PAYMENTS COLLECTION ==============
interface Payment {
  id: string;
  orderId: string;
  userId: string;
  amount: number;
  currency: string;
  provider: 'stripe' | 'jazzcash' | 'easypaisa';
  status: 'pending' | 'completed' | 'failed';
  transactionId: string;
  metadata: Record<string, any>;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}
```

### Database Collection Rules

```typescript
// Firestore structure hierarchy
/users                           // Root collection
  /{userId}                      // Document
    /addresses                   // Subcollection (1:many relationship)
      /{addressId}               // Document
    /orders                      // Subcollection reference
      /{orderId}                 // Document
        /items                   // Nested subcollection
          /{itemId}              // Document

/products                        // Root collection
  /{productId}                   // Document
    /reviews                     // Subcollection
      /{reviewId}                // Document
    /inventory                   // Subcollection (versioning)
      /{timestamp}               // Document

/orders                          // Root collection (for global queries)
  /{orderId}                     // Document
    /payments                    // Subcollection
      /{paymentId}               // Document
    /history                     // Subcollection (audit trail)
      /{eventId}                 // Document

/categories                      // Root collection
  /{categoryId}                  // Document

/payments                        // Root collection (for global payments view)
  /{paymentId}                   // Document
```

## Denormalization Strategy

### When to Denormalize

```typescript
// BAD: Over-normalized (too many reads)
users/{userId}/orders/{orderId} -> requires reading order document
                                -> then reading product documents
                                -> then reading user data again
// Result: N+1 query problem

// GOOD: Denormalized for common access patterns
orders/{orderId} contains:
{
  userId: string,
  userEmail: string,           // Denormalized for email notifications
  userName: string,            // Denormalized for order lists
  items: [                      // Denormalized product data
    {
      productId: string,
      productName: string,
      price: number,
      image: string
    }
  ],
  shippingCost: number,        // Denormalized for totals
  taxAmount: number
}
```

### Denormalization Synchronization

```typescript
// Cloud Function to sync denormalized data
import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

const db = admin.firestore();

// When product price changes, update all denormalized copies
export const syncProductPrice = functions.firestore
  .document('products/{productId}')
  .onUpdate(async (change, context) => {
    const productId = context.params.productId;
    const newData = change.after.data();
    const oldData = change.before.data();

    // Only sync if price changed
    if (newData.price === oldData.price) return;

    const batch = db.batch();
    const ordersSnapshot = await db.collection('orders')
      .where('items', 'array-contains', { productId })
      .get();

    ordersSnapshot.docs.forEach(doc => {
      const items = doc.data().items.map(item => 
        item.productId === productId 
          ? { ...item, price: newData.price }
          : item
      );
      batch.update(doc.ref, { items });
    });

    await batch.commit();
  });
```

## Pagination Implementation

```typescript
// Efficient pagination with Firestore
interface PaginationState {
  pageSize: number;
  lastVisible?: FirebaseFirestore.DocumentSnapshot;
  lastDocId?: string;
}

async function getProductsPage(
  pageSize: number = 20,
  lastDocId?: string
): Promise<{ products: Product[]; lastDocId?: string }> {
  let query: FirebaseFirestore.Query = db.collection('products')
    .where('isActive', '==', true)
    .orderBy('createdAt', 'desc')
    .limit(pageSize + 1); // Get one extra to know if more exists

  if (lastDocId) {
    const lastDoc = await db.collection('products').doc(lastDocId).get();
    query = query.startAfter(lastDoc);
  }

  const snapshot = await query.get();
  const docs = snapshot.docs.slice(0, pageSize);
  const hasMore = snapshot.docs.length > pageSize;

  return {
    products: docs.map(doc => ({ id: doc.id, ...doc.data() } as Product)),
    lastDocId: hasMore ? docs[docs.length - 1].id : undefined
  };
}

// Usage with React
export const useProducts = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [lastDocId, setLastDocId] = useState<string>();
  const [hasMore, setHasMore] = useState(true);

  const loadMore = async () => {
    const result = await getProductsPage(20, lastDocId);
    setProducts(prev => [...prev, ...result.products]);
    setLastDocId(result.lastDocId);
    setHasMore(!!result.lastDocId);
  };

  useEffect(() => {
    loadMore();
  }, []);

  return { products, hasMore, loadMore };
};
```

## Batch Operations

```typescript
// Efficient batch writes for multiple documents
async function createOrderWithItems(
  order: Order,
  items: OrderItem[],
  userId: string
): Promise<string> {
  const batch = db.batch();
  const orderRef = db.collection('orders').doc();

  // Add order
  batch.set(orderRef, {
    ...order,
    id: orderRef.id,
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
  });

  // Add items subcollection
  items.forEach(item => {
    const itemRef = orderRef.collection('items').doc();
    batch.set(itemRef, item);
  });

  // Update user's order count
  const userRef = db.collection('users').doc(userId);
  batch.update(userRef, {
    metadata: {
      totalOrders: admin.firestore.FieldValue.increment(1),
      totalSpent: admin.firestore.FieldValue.increment(order.pricing.total),
    }
  });

  // Update product inventory
  items.forEach(item => {
    const productRef = db.collection('products').doc(item.productId);
    batch.update(productRef, {
      'inventory.reserved': admin.firestore.FieldValue.increment(item.quantity),
      'inventory.available': admin.firestore.FieldValue.increment(-item.quantity),
    });
  });

  await batch.commit();
  return orderRef.id;
}
```

## Transactions

```typescript
// ACID transaction for order processing
async function processOrderPayment(
  orderId: string,
  paymentId: string,
  amount: number
): Promise<void> {
  const transaction = db.transaction();

  try {
    const result = await transaction.runTransaction(async (txn) => {
      // Read order
      const orderRef = db.collection('orders').doc(orderId);
      const orderDoc = await txn.get(orderRef);

      if (!orderDoc.exists) {
        throw new Error('Order not found');
      }

      const order = orderDoc.data() as Order;

      // Verify amount matches
      if (order.pricing.total !== amount) {
        throw new Error('Amount mismatch');
      }

      // Check order status
      if (order.status !== 'pending') {
        throw new Error('Order already processed');
      }

      // Create payment record
      const paymentRef = db.collection('payments').doc(paymentId);
      txn.set(paymentRef, {
        orderId,
        userId: order.userId,
        amount,
        status: 'completed',
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      // Update order status
      txn.update(orderRef, {
        status: 'confirmed',
        'payment.status': 'completed',
        'payment.transactionId': paymentId,
        updatedAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      // Update user's order metadata
      const userRef = db.collection('users').doc(order.userId);
      txn.update(userRef, {
        'metadata.totalSpent': admin.firestore.FieldValue.increment(amount),
      });

      return { success: true, paymentRef: paymentRef.id };
    });

    console.log('Payment processed:', result);
  } catch (error) {
    console.error('Transaction failed:', error);
    throw error;
  }
}
```

## Composite Indexes

```json
{
  "indexes": [
    {
      "collectionGroup": "products",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "category", "order": "ASCENDING" },
        { "fieldPath": "price", "order": "ASCENDING" },
        { "fieldPath": "rating", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "orders",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "userId", "order": "ASCENDING" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "orders",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "status", "order": "ASCENDING" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    }
  ]
}
```

## Real-Time Listeners

```typescript
// Efficient real-time listeners with optimization
class FirestoreListener {
  private unsubscribers: (() => void)[] = [];

  // Listen to user's orders with real-time updates
  subscribeToUserOrders(userId: string, callback: (orders: Order[]) => void) {
    const unsubscribe = db.collection('orders')
      .where('userId', '==', userId)
      .orderBy('createdAt', 'desc')
      .limit(20)
      .onSnapshot(
        (snapshot) => {
          const orders = snapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data()
          } as Order));
          callback(orders);
        },
        (error) => {
          console.error('Listener error:', error);
        }
      );

    this.unsubscribers.push(unsubscribe);
    return unsubscribe;
  }

  // Listen with offline persistence
  subscribeWithPersistence(
    userId: string,
    callback: (data: any, source: 'cache' | 'server') => void
  ) {
    return db.collection('users')
      .doc(userId)
      .onSnapshot({ includeMetadataChanges: true }, (snapshot) => {
        const source = snapshot.metadata.hasPendingWrites ? 'cache' : 'server';
        callback(snapshot.data(), source);
      });
  }

  unsubscribeAll() {
    this.unsubscribers.forEach(unsubscribe => unsubscribe());
    this.unsubscribers = [];
  }
}
```

## Cleanup and Migration

```typescript
// Archive old orders (data retention policy)
export const archiveOldOrders = functions.pubsub
  .schedule('0 2 * * 0') // Weekly at 2 AM
  .timeZone('America/New_York')
  .onRun(async (context) => {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const oldOrders = await db.collection('orders')
      .where('createdAt', '<', admin.firestore.Timestamp.fromDate(thirtyDaysAgo))
      .where('status', 'in', ['delivered', 'cancelled', 'refunded'])
      .get();

    const batch = db.batch();
    const archiveBatch = db.batch();

    oldOrders.docs.forEach(doc => {
      const data = doc.data();
      
      // Move to archive collection
      archiveBatch.set(db.collection('orders_archive').doc(doc.id), {
        ...data,
        archivedAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      // Delete from active collection
      batch.delete(doc.ref);
    });

    await batch.commit();
    await archiveBatch.commit();

    console.log(`Archived ${oldOrders.size} old orders`);
  });
```