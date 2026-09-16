# Next.js/React Frontend Integration

## Project Setup

### Create Next.js Project with TypeScript

```bash
npx create-next-app@latest my-app --typescript --tailwind --app
cd my-app
npm install axios zustand zod
```

### Environment Configuration

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# API URLs
NEXT_PUBLIC_AUTH_API_URL=${NEXT_PUBLIC_API_URL}/api/v1/auth
NEXT_PUBLIC_USERS_API_URL=${NEXT_PUBLIC_API_URL}/api/v1/users
NEXT_PUBLIC_PAYMENTS_API_URL=${NEXT_PUBLIC_API_URL}/api/v1/payments
```

## API Client Setup

### Axios Instance with Interceptors

```typescript
// lib/api-client.ts
import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig
} from 'axios';
import { useRouter } from 'next/router';

const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor - add token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle 401 and refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefreshToken);

        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### API Service Hooks

```typescript
// lib/api-services.ts
import apiClient from './api-client';
import { AxiosError } from 'axios';

// Types
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'admin' | 'moderator';
  email_verified: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
}

export interface PaymentResponse {
  id: number;
  amount: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  created_at: string;
}

// Authentication Services
export const authAPI = {
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await apiClient.post<AuthResponse>(
      '/api/v1/auth/login',
      formData,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/api/v1/auth/register', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/api/v1/auth/logout');
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/v1/auth/me');
    return response.data;
  },

  requestPasswordReset: async (email: string): Promise<{ message: string }> => {
    const response = await apiClient.post('/api/v1/auth/forgot-password', { email });
    return response.data;
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    const response = await apiClient.post('/api/v1/auth/reset-password', {
      token,
      new_password: newPassword
    });
    return response.data;
  }
};

// User Services
export const usersAPI = {
  getUsers: async (skip: number = 0, limit: number = 10): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/api/v1/users', {
      params: { skip, limit }
    });
    return response.data;
  },

  getUser: async (userId: number): Promise<User> => {
    const response = await apiClient.get<User>(`/api/v1/users/${userId}`);
    return response.data;
  },

  updateUser: async (userId: number, data: Partial<User>): Promise<User> => {
    const response = await apiClient.put<User>(`/api/v1/users/${userId}`, data);
    return response.data;
  },

  deleteUser: async (userId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/api/v1/users/${userId}`);
    return response.data;
  }
};

// Payment Services
export const paymentsAPI = {
  createCheckoutSession: async (amount: number, description: string) => {
    const response = await apiClient.post('/api/v1/payments/checkout', {
      amount,
      currency: 'usd',
      description,
      success_url: `${window.location.origin}/payment/success`,
      cancel_url: `${window.location.origin}/payment/cancel`
    });
    return response.data;
  },

  getPaymentStatus: async (paymentId: number): Promise<PaymentResponse> => {
    const response = await apiClient.get<PaymentResponse>(
      `/api/v1/payments/${paymentId}`
    );
    return response.data;
  },

  listPayments: async (skip: number = 0, limit: number = 10): Promise<PaymentResponse[]> => {
    const response = await apiClient.get<PaymentResponse[]>('/api/v1/payments', {
      params: { skip, limit }
    });
    return response.data;
  }
};
```

## State Management with Zustand

### Auth Store

```typescript
// store/auth-store.ts
import { create } from 'zustand';
import { authAPI, User, AuthResponse } from '@/lib/api-services';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<void>;
  setToken: (token: string) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token') || null,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.login({ username: email, password });
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      set({ token: response.access_token, isLoading: false });

      // Fetch user data
      const user = await authAPI.getCurrentUser();
      set({ user });
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  register: async (email: string, fullName: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const user = await authAPI.register({
        email,
        full_name: fullName,
        password
      });
      set({ user, isLoading: false });
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Registration failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({ user: null, token: null });
    }
  },

  fetchCurrentUser: async () => {
    set({ isLoading: true });
    try {
      const user = await authAPI.getCurrentUser();
      set({ user, isLoading: false });
    } catch (error: any) {
      set({ error: 'Failed to fetch user', isLoading: false });
      throw error;
    }
  },

  setToken: (token: string) => {
    localStorage.setItem('access_token', token);
    set({ token });
  },

  clearError: () => set({ error: null })
}));
```

## Authentication Pages

### Login Page

```typescript
// app/login/page.tsx
'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth-store';

export default function LoginPage() {
  const router = useRouter();
  const { login, error, isLoading } = useAuthStore();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      await login(formData.email, formData.password);
      router.push('/dashboard');
    } catch (error) {
      // Error is handled by store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Login</h2>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <Link href="/register" className="text-blue-600 hover:underline">
            Register
          </Link>
        </p>

        <p className="mt-2 text-center text-sm text-gray-600">
          <Link href="/forgot-password" className="text-blue-600 hover:underline">
            Forgot password?
          </Link>
        </p>
      </div>
    </div>
  );
}
```

### Protected Route Component

```typescript
// components/ProtectedRoute.tsx
'use client';

import { useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/auth-store';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: 'admin' | 'moderator' | 'user';
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token, isLoading } = useAuthStore();

  useEffect(() => {
    // Check if already loading
    if (isLoading) return;

    // Redirect if no token
    if (!token) {
      router.push(`/login?redirect=${pathname}`);
      return;
    }

    // Check role if required
    if (requiredRole && user?.role !== requiredRole) {
      router.push('/unauthorized');
    }
  }, [token, user, isLoading, router, pathname, requiredRole]);

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return <>{children}</>;
}
```

## Payment Integration

### Stripe Checkout Component

```typescript
// components/StripeCheckout.tsx
'use client';

import { useState } from 'react';
import { loadStripe } from '@stripe/js';
import { paymentsAPI } from '@/lib/api-services';

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

interface StripeCheckoutProps {
  amount: number;
  description: string;
  onSuccess?: () => void;
}

export default function StripeCheckout({ amount, description, onSuccess }: StripeCheckoutProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCheckout = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const stripe = await stripePromise;
      if (!stripe) throw new Error('Stripe not loaded');

      const response = await paymentsAPI.createCheckoutSession(amount, description);

      const result = await stripe.redirectToCheckout({
        sessionId: response.session_id
      });

      if (result.error) {
        setError(result.error.message || 'Checkout failed');
      } else if (onSuccess) {
        onSuccess();
      }
    } catch (error: any) {
      setError(error.message || 'Payment failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded text-red-800">
          {error}
        </div>
      )}

      <div className="p-4 bg-gray-50 rounded">
        <p className="text-lg font-semibold">{description}</p>
        <p className="text-2xl font-bold text-blue-600">${(amount / 100).toFixed(2)}</p>
      </div>

      <button
        onClick={handleCheckout}
        disabled={isLoading}
        className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-semibold"
      >
        {isLoading ? 'Processing...' : `Pay $${(amount / 100).toFixed(2)}`}
      </button>
    </div>
  );
}
```

## Error Handling

```typescript
// lib/error-handler.ts
import { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  statusCode: number;
  details?: Record<string, any>;
}

export const handleApiError = (error: unknown): ApiError => {
  if (error instanceof AxiosError) {
    return {
      message: error.response?.data?.detail || error.message || 'An error occurred',
      statusCode: error.response?.status || 500,
      details: error.response?.data
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      statusCode: 500
    };
  }

  return {
    message: 'An unknown error occurred',
    statusCode: 500
  };
};
```

## CORS Configuration

For development, ensure FastAPI CORS settings match your Next.js frontend:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "https://yourdomain.com"  # Production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)
```

## Deployment

### Environment Variables for Production

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### Docker (Next.js)

```dockerfile
# Dockerfile.web
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000
CMD ["npm", "run", "start"]
```

## Type Safety

Generate TypeScript types from FastAPI OpenAPI schema:

```bash
npm install -D @openapi-typescript/openapi-typescript

# Generate types
npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts
```

Use generated types:

```typescript
import { paths } from '@/lib/api-types';

type GetUsersResponse = paths['/api/v1/users']['get']['responses']['200']['content']['application/json'];
type CreateUserRequest = paths['/api/v1/users']['post']['requestBody']['content']['application/json'];
```