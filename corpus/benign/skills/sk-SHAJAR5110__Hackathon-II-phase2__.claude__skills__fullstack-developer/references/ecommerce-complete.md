# Complete E-Commerce Implementation Guide

## Project Structure

```
ecommerce-app/
├── app/
│   ├── layout.tsx                    # Root layout
│   ├── page.tsx                      # Home page
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── layout.tsx
│   ├── (admin)/
│   │   ├── dashboard/page.tsx
│   │   ├── products/page.tsx
│   │   └── layout.tsx
│   ├── products/
│   │   ├── page.tsx                  # Product list
│   │   ├── [id]/page.tsx             # Product detail
│   │   └── layout.tsx
│   ├── cart/page.tsx
│   ├── checkout/
│   │   ├── page.tsx
│   │   └── success/page.tsx
│   └── api/
│       ├── auth/[...nextauth]/route.ts
│       ├── products/route.ts
│       ├── orders/route.ts
│       ├── checkout/route.ts
│       ├── webhooks/stripe/route.ts
│       └── upload/route.ts
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Navigation.tsx
│   │   └── Sidebar.tsx
│   ├── products/
│   │   ├── ProductCard.tsx
│   │   ├── ProductList.tsx
│   │   ├── ProductDetail.tsx
│   │   └── ProductFilter.tsx
│   ├── cart/
│   │   ├── CartItem.tsx
│   │   ├── CartSummary.tsx
│   │   └── CartActions.tsx
│   ├── checkout/
│   │   ├── CheckoutForm.tsx
│   │   ├── PaymentForm.tsx
│   │   └── OrderSummary.tsx
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   └── AuthGuard.tsx
│   └── common/
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Modal.tsx
│       └── Toast.tsx
├── lib/
│   ├── firebase.ts                   # Firebase initialization
│   ├── auth.ts                       # Auth helpers
│   ├── firestore.ts                  # Firestore helpers
│   ├── stripe.ts                     # Stripe helpers
│   ├── validation.ts                 # Zod schemas
│   ├── types.ts                      # Type definitions
│   └── utils.ts                      # Utility functions
├── hooks/
│   ├── useAuth.ts
│   ├── useCart.ts
│   ├── useProducts.ts
│   ├── useOrders.ts
│   └── useForms.ts
├── store/
│   ├── authStore.ts                  # Zustand auth store
│   ├── cartStore.ts                  # Zustand cart store
│   └── uiStore.ts                    # Zustand UI store
├── styles/
│   └── globals.css
├── public/
│   ├── images/
│   └── icons/
├── .env.local.example
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── next.config.js
```

## Core Files Implementation

### 1. Firebase Setup & Types

```typescript
// lib/firebase.ts
import { initializeApp } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';
import { getFirestore, Firestore } from 'firebase/firestore';
import { getStorage, FirebaseStorage } from 'firebase/storage';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const auth: Auth = getAuth(app);
export const db: Firestore = getFirestore(app);
export const storage: FirebaseStorage = getStorage(app);

export default app;
```

```typescript
// lib/types.ts
export interface User {
  uid: string;
  email: string;
  displayName?: string;
  photoURL?: string;
  role: 'customer' | 'vendor' | 'admin';
  createdAt: Date;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  originalPrice?: number;
  images: string[];
  category: string;
  tags: string[];
  inventory: {
    total: number;
    available: number;
  };
  rating: number;
  reviewCount: number;
  vendorId: string;
  createdAt: Date;
  isActive: boolean;
}

export interface CartItem {
  productId: string;
  name: string;
  price: number;
  image: string;
  quantity: number;
  addedAt: Date;
}

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  shipping: ShippingInfo;
  billing: BillingInfo;
  pricing: {
    subtotal: number;
    tax: number;
    shipping: number;
    discount: number;
    total: number;
  };
  payment: {
    method: 'stripe' | 'jazzcash' | 'easypaisa';
    status: 'pending' | 'completed' | 'failed';
    transactionId?: string;
  };
  status: 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';
  createdAt: Date;
  updatedAt: Date;
}

export interface OrderItem {
  productId: string;
  name: string;
  quantity: number;
  price: number;
  image: string;
}

export interface ShippingInfo {
  fullName: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
}

export interface BillingInfo {
  isSameAsShipping: boolean;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;
}
```

### 2. Firestore Schema & Helpers

```typescript
// lib/firestore.ts
import { 
  collection, 
  doc, 
  getDoc, 
  getDocs, 
  query, 
  where, 
  addDoc, 
  updateDoc,
  writeBatch,
  Timestamp,
  QueryConstraint
} from 'firebase/firestore';
import { db } from './firebase';
import { Product, Order, User } from './types';

// Collections
export const usersCollection = collection(db, 'users');
export const productsCollection = collection(db, 'products');
export const ordersCollection = collection(db, 'orders');
export const paymentsCollection = collection(db, 'payments');

// Get product by ID
export async function getProductById(productId: string): Promise<Product | null> {
  try {
    const docRef = doc(productsCollection, productId);
    const docSnap = await getDoc(docRef);
    
    if (!docSnap.exists()) return null;
    
    return {
      id: docSnap.id,
      ...docSnap.data(),
      createdAt: docSnap.data().createdAt?.toDate(),
    } as Product;
  } catch (error) {
    console.error('Error getting product:', error);
    throw error;
  }
}

// Get all active products with filters
export async function getProducts(
  filters?: {
    category?: string;
    minPrice?: number;
    maxPrice?: number;
    search?: string;
  }
): Promise<Product[]> {
  try {
    const constraints: QueryConstraint[] = [
      where('isActive', '==', true),
    ];

    if (filters?.category) {
      constraints.push(where('category', '==', filters.category));
    }

    const q = query(productsCollection, ...constraints);
    const querySnapshot = await getDocs(q);
    
    let products = querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      createdAt: doc.data().createdAt?.toDate(),
    } as Product));

    // Apply additional filters (price range, search)
    if (filters?.minPrice) {
      products = products.filter(p => p.price >= filters.minPrice!);
    }
    if (filters?.maxPrice) {
      products = products.filter(p => p.price <= filters.maxPrice!);
    }
    if (filters?.search) {
      const searchLower = filters.search.toLowerCase();
      products = products.filter(p => 
        p.name.toLowerCase().includes(searchLower) ||
        p.description.toLowerCase().includes(searchLower)
      );
    }

    return products;
  } catch (error) {
    console.error('Error getting products:', error);
    throw error;
  }
}

// Create order with items
export async function createOrder(orderData: Omit<Order, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
  try {
    const batch = writeBatch(db);
    const orderRef = doc(collection(db, 'orders'));

    const orderPayload = {
      ...orderData,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now(),
    };

    batch.set(orderRef, orderPayload);

    // Update inventory
    for (const item of orderData.items) {
      const productRef = doc(productsCollection, item.productId);
      batch.update(productRef, {
        'inventory.available': -item.quantity,
      });
    }

    // Update user's order count
    const userRef = doc(usersCollection, orderData.userId);
    batch.update(userRef, {
      'metadata.lastOrderDate': Timestamp.now(),
    });

    await batch.commit();
    return orderRef.id;
  } catch (error) {
    console.error('Error creating order:', error);
    throw error;
  }
}

// Get user's orders
export async function getUserOrders(userId: string): Promise<Order[]> {
  try {
    const q = query(
      ordersCollection,
      where('userId', '==', userId)
    );
    const querySnapshot = await getDocs(q);
    
    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      createdAt: doc.data().createdAt?.toDate(),
      updatedAt: doc.data().updatedAt?.toDate(),
    } as Order));
  } catch (error) {
    console.error('Error getting orders:', error);
    throw error;
  }
}
```

### 3. Zustand Cart Store

```typescript
// store/cartStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { CartItem } from '@/lib/types';

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  
  // Computed
  getSubtotal: () => number;
  getTotal: () => number;
  getItemCount: () => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (item) => {
        set(state => {
          const existing = state.items.find(i => i.productId === item.productId);
          if (existing) {
            return {
              items: state.items.map(i =>
                i.productId === item.productId
                  ? { ...i, quantity: i.quantity + item.quantity }
                  : i
              ),
            };
          }
          return { items: [...state.items, item] };
        });
      },

      removeItem: (productId) => {
        set(state => ({
          items: state.items.filter(i => i.productId !== productId),
        }));
      },

      updateQuantity: (productId, quantity) => {
        set(state => ({
          items: state.items.map(i =>
            i.productId === productId ? { ...i, quantity } : i
          ),
        }));
      },

      clearCart: () => {
        set({ items: [] });
      },

      getSubtotal: () => {
        return get().items.reduce((sum, item) => sum + item.price * item.quantity, 0);
      },

      getTotal: () => {
        const subtotal = get().getSubtotal();
        const tax = subtotal * 0.1; // 10% tax
        const shipping = subtotal > 100 ? 0 : 10; // Free shipping over $100
        return subtotal + tax + shipping;
      },

      getItemCount: () => {
        return get().items.reduce((sum, item) => sum + item.quantity, 0);
      },
    }),
    {
      name: 'cart-storage',
    }
  )
);
```

### 4. Authentication Setup

```typescript
// lib/auth.ts
import { 
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';
import { doc, setDoc } from 'firebase/firestore';
import { auth, db } from './firebase';
import { User } from './types';

export async function registerUser(
  email: string,
  password: string,
  displayName: string
): Promise<User> {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const firebaseUser = userCredential.user;

    const user: User = {
      uid: firebaseUser.uid,
      email: firebaseUser.email || '',
      displayName,
      role: 'customer',
      createdAt: new Date(),
    };

    await setDoc(doc(db, 'users', firebaseUser.uid), user);
    return user;
  } catch (error) {
    throw error;
  }
}

export async function loginUser(email: string, password: string): Promise<User> {
  try {
    await signInWithEmailAndPassword(auth, email, password);
    const user = auth.currentUser;
    if (!user) throw new Error('User not found');

    return {
      uid: user.uid,
      email: user.email || '',
      displayName: user.displayName || '',
      role: 'customer',
      createdAt: new Date(),
    };
  } catch (error) {
    throw error;
  }
}

export async function logoutUser(): Promise<void> {
  await signOut(auth);
}

export function onAuthChange(callback: (user: FirebaseUser | null) => void) {
  return onAuthStateChanged(auth, callback);
}
```

### 5. Validation Schemas

```typescript
// lib/validation.ts
import { z } from 'zod';

export const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  displayName: z.string().min(2, 'Name must be at least 2 characters'),
}).refine(data => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

export const checkoutSchema = z.object({
  fullName: z.string().min(2, 'Name is required'),
  email: z.string().email('Invalid email'),
  phone: z.string().min(10, 'Invalid phone number'),
  address: z.string().min(5, 'Address is required'),
  city: z.string().min(2, 'City is required'),
  state: z.string().min(2, 'State is required'),
  postalCode: z.string().min(3, 'Postal code is required'),
  country: z.string().min(2, 'Country is required'),
});

export const productSchema = z.object({
  name: z.string().min(3, 'Product name is required'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  price: z.number().positive('Price must be greater than 0'),
  category: z.string().min(1, 'Category is required'),
  images: z.array(z.string().url()).min(1, 'At least one image is required'),
});

export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type CheckoutInput = z.infer<typeof checkoutSchema>;
export type ProductInput = z.infer<typeof productSchema>;
```

### 6. API Routes

```typescript
// app/api/checkout/route.ts
import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { getProductById } from '@/lib/firestore';
import { checkoutSchema } from '@/lib/validation';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { items, shippingInfo, paymentMethod } = body;

    // Validate input
    const shippingValidation = checkoutSchema.safeParse(shippingInfo);
    if (!shippingValidation.success) {
      return NextResponse.json(
        { error: shippingValidation.error.errors },
        { status: 400 }
      );
    }

    // Calculate total
    let total = 0;
    for (const item of items) {
      const product = await getProductById(item.productId);
      if (!product) {
        return NextResponse.json(
          { error: `Product ${item.productId} not found` },
          { status: 404 }
        );
      }
      total += product.price * item.quantity;
    }

    // Create Stripe payment intent
    if (paymentMethod === 'stripe') {
      const paymentIntent = await stripe.paymentIntents.create({
        amount: Math.round(total * 100),
        currency: 'usd',
        metadata: {
          items: JSON.stringify(items),
        },
      });

      return NextResponse.json({
        clientSecret: paymentIntent.client_secret,
        paymentIntentId: paymentIntent.id,
      });
    }

    // Handle JazzCash or EasyPaisa
    return NextResponse.json({
      success: true,
      total,
    });
  } catch (error) {
    console.error('Checkout error:', error);
    return NextResponse.json(
      { error: 'Checkout failed' },
      { status: 500 }
    );
  }
}
```

```typescript
// app/api/webhooks/stripe/route.ts
import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { createOrder } from '@/lib/firestore';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '');

export async function POST(request: NextRequest) {
  const sig = request.headers.get('stripe-signature') || '';
  const body = await request.text();

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET || ''
    );

    if (event.type === 'payment_intent.succeeded') {
      const paymentIntent = event.data.object as Stripe.PaymentIntent;
      
      // Create order in database
      console.log('Payment succeeded:', paymentIntent.id);
      // Process order creation here
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 400 }
    );
  }
}
```

### 7. React Component Examples

```typescript
// components/products/ProductCard.tsx
import Image from 'next/image';
import Link from 'next/link';
import { Product } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Star } from 'lucide-react';

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow overflow-hidden">
      <Link href={`/products/${product.id}`}>
        <div className="relative h-48 w-full">
          <Image
            src={product.images[0]}
            alt={product.name}
            fill
            className="object-cover"
          />
        </div>
      </Link>

      <div className="p-4">
        <Link href={`/products/${product.id}`}>
          <h3 className="text-lg font-semibold text-gray-900 hover:text-blue-600 mb-2">
            {product.name}
          </h3>
        </Link>

        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {product.description}
        </p>

        <div className="flex items-center mb-3">
          <div className="flex items-center">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                size={16}
                className={i < Math.floor(product.rating) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}
              />
            ))}
          </div>
          <span className="text-sm text-gray-500 ml-2">({product.reviewCount})</span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">
              ${product.price.toFixed(2)}
            </span>
            {product.originalPrice && (
              <span className="text-sm text-gray-500 line-through">
                ${product.originalPrice.toFixed(2)}
              </span>
            )}
          </div>
          <Button
            size="sm"
            variant={product.inventory.available > 0 ? 'default' : 'disabled'}
          >
            {product.inventory.available > 0 ? 'Add to Cart' : 'Out of Stock'}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

```typescript
// components/auth/LoginForm.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginSchema, LoginInput } from '@/lib/validation';
import { loginUser } from '@/lib/auth';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import toast from 'react-hot-toast';

export function LoginForm() {
  const router = useRouter();
  const setUser = useAuthStore(state => state.setUser);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginInput) => {
    setIsLoading(true);
    try {
      const user = await loginUser(data.email, data.password);
      setUser(user);
      toast.success('Logged in successfully!');
      router.push('/');
    } catch (error: any) {
      toast.error(error.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Email
        </label>
        <Input
          {...register('email')}
          type="email"
          placeholder="your@email.com"
          className={errors.email ? 'border-red-500' : ''}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-500">{errors.email.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Password
        </label>
        <Input
          {...register('password')}
          type="password"
          placeholder="••••••••"
          className={errors.password ? 'border-red-500' : ''}
        />
        {errors.password && (
          <p className="mt-1 text-sm text-red-500">{errors.password.message}</p>
        )}
      </div>

      <Button type="submit" disabled={isLoading} className="w-full">
        {isLoading ? 'Logging in...' : 'Login'}
      </Button>
    </form>
  );
}
```

## Key Patterns

**Error Handling:**
```typescript
try {
  // Operation
} catch (error) {
  const message = error instanceof Error ? error.message : 'Unknown error';
  toast.error(message);
  console.error('Error:', error);
}
```

**Loading States:**
```typescript
const [isLoading, setIsLoading] = useState(false);

const handleAction = async () => {
  setIsLoading(true);
  try {
    await someAsyncAction();
  } finally {
    setIsLoading(false);
  }
};
```

**Type Safety:**
```typescript
// Always type API responses
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

const response: ApiResponse<Order> = await fetch('/api/orders').then(r => r.json());
```

This complete implementation provides a production-ready e-commerce platform foundation!