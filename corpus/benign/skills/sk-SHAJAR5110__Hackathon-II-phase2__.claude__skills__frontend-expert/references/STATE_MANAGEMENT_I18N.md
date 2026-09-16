# STATE MANAGEMENT & INTERNATIONALIZATION

## 1. REDUX ADVANCED PATTERNS

### Redux DevTools Configuration

```typescript
// store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import { composeWithDevTools } from 'redux-devtools-extension';

export const store = configureStore(
    {
        reducer: {
            // reducers
        },
        middleware: (getDefaultMiddleware) =>
            getDefaultMiddleware({
                serializableCheck: {
                    ignoredActions: ['auth/login/fulfilled'],
                    ignoredPaths: ['auth.user.loginDate'],
                },
            }),
        devTools:
            process.env.NODE_ENV !== 'production' &&
            typeof window !== 'undefined',
    }
);
```

### Async Thunks with Error Handling

```typescript
// store/slices/user.ts
import {
    createSlice,
    createAsyncThunk,
    PayloadAction,
    AnyAction,
} from '@reduxjs/toolkit';

export interface User {
    id: string;
    email: string;
    name: string;
    avatar?: string;
}

interface UserState {
    byId: Record<string, User>;
    allIds: string[];
    loading: boolean;
    error: string | null;
    lastUpdated: number | null;
}

const initialState: UserState = {
    byId: {},
    allIds: [],
    loading: false,
    error: null,
    lastUpdated: null,
};

/**
 * Fetch users with automatic retry
 */
export const fetchUsers = createAsyncThunk<
    User[],
    undefined,
    {
        rejectValue: { message: string; code: string };
    }
>('users/fetchUsers', async (_, { rejectWithValue }) => {
    try {
        const response = await fetch('/api/users', {
            signal: AbortSignal.timeout(10000), // 10s timeout
        });

        if (!response.ok) {
            return rejectWithValue({
                message: `HTTP ${response.status}`,
                code: `HTTP_${response.status}`,
            });
        }

        return await response.json();
    } catch (error) {
        if (error instanceof Error) {
            return rejectWithValue({
                message: error.message,
                code: 'FETCH_ERROR',
            });
        }
        return rejectWithValue({
            message: 'Unknown error',
            code: 'UNKNOWN_ERROR',
        });
    }
});

/**
 * Update user with optimistic updates
 */
export const updateUser = createAsyncThunk<
    User,
    { id: string; data: Partial<User> },
    { state: { users: UserState }; rejectValue: { message: string } }
>('users/updateUser', async ({ id, data }, { rejectWithValue, getState }) => {
    try {
        const response = await fetch(`/api/users/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        return rejectWithValue({
            message: error instanceof Error ? error.message : 'Update failed',
        });
    }
});

export const userSlice = createSlice({
    name: 'users',
    initialState,
    reducers: {
        userAdded: (state, action: PayloadAction<User>) => {
            state.byId[action.payload.id] = action.payload;
            if (!state.allIds.includes(action.payload.id)) {
                state.allIds.push(action.payload.id);
            }
        },
        userRemoved: (state, action: PayloadAction<string>) => {
            delete state.byId[action.payload];
            state.allIds = state.allIds.filter((id) => id !== action.payload);
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchUsers.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchUsers.fulfilled, (state, action) => {
                state.loading = false;
                state.byId = {};
                state.allIds = [];

                action.payload.forEach((user) => {
                    state.byId[user.id] = user;
                    state.allIds.push(user.id);
                });

                state.lastUpdated = Date.now();
            })
            .addCase(fetchUsers.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload?.message || 'Failed to fetch';
            })
            .addCase(updateUser.fulfilled, (state, action) => {
                state.byId[action.payload.id] = action.payload;
            })
            .addCase(updateUser.rejected, (state, action) => {
                state.error = action.payload?.message || 'Failed to update';
            });
    },
});

export default userSlice.reducer;

// Selectors
export const selectAllUsers = (state: { users: UserState }) =>
    state.users.allIds.map((id) => state.users.byId[id]);

export const selectUserById = (state: { users: UserState }, id: string) =>
    state.users.byId[id];

export const selectUsersLoading = (state: { users: UserState }) =>
    state.users.loading;

export const selectUsersError = (state: { users: UserState }) =>
    state.users.error;
```

## 2. ZUSTAND ADVANCED PATTERNS

### Complex State with Persistence

```typescript
// store/app.store.ts
import { create } from 'zustand';
import { devtools, persist, immer } from 'zustand/middleware';

interface AppStore {
    // User state
    user: { id: string; email: string; role: string } | null;
    setUser: (user: AppStore['user']) => void;

    // UI state
    sidebarOpen: boolean;
    toggleSidebar: () => void;

    // Theme
    theme: 'light' | 'dark';
    setTheme: (theme: 'light' | 'dark') => void;

    // Notifications
    notifications: Array<{ id: string; message: string; type: string }>;
    addNotification: (message: string, type: string) => void;
    removeNotification: (id: string) => void;

    // Async operations
    loading: boolean;
    setLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppStore>()(
    devtools(
        persist(
            immer((set) => ({
                user: null,
                setUser: (user) => set({ user }),

                sidebarOpen: true,
                toggleSidebar: () =>
                    set((state) => {
                        state.sidebarOpen = !state.sidebarOpen;
                    }),

                theme: 'light',
                setTheme: (theme) => set({ theme }),

                notifications: [],
                addNotification: (message, type) =>
                    set((state) => {
                        state.notifications.push({
                            id: Date.now().toString(),
                            message,
                            type,
                        });
                    }),
                removeNotification: (id) =>
                    set((state) => {
                        state.notifications = state.notifications.filter(
                            (n) => n.id !== id
                        );
                    }),

                loading: false,
                setLoading: (loading) => set({ loading }),
            })),
            {
                name: 'app-store',
                partialize: (state) => ({
                    theme: state.theme,
                    sidebarOpen: state.sidebarOpen,
                }),
            }
        ),
        { name: 'AppStore' }
    )
);
```

## 3. INTERNATIONALIZATION (i18n)

### Next.js i18n Configuration

```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
    i18n: {
        locales: ['en', 'es', 'fr', 'de', 'ja', 'zh'],
        defaultLocale: 'en',
        localeDetection: true,
    },
};

module.exports = nextConfig;
```

### Translation Files

```json
// public/locales/en/common.json
{
    "header": {
        "title": "Welcome",
        "navigation": {
            "home": "Home",
            "about": "About",
            "contact": "Contact"
        }
    },
    "auth": {
        "login": "Login",
        "logout": "Logout",
        "email": "Email Address",
        "password": "Password"
    }
}

// public/locales/es/common.json
{
    "header": {
        "title": "Bienvenido",
        "navigation": {
            "home": "Inicio",
            "about": "Acerca de",
            "contact": "Contacto"
        }
    },
    "auth": {
        "login": "Iniciar sesión",
        "logout": "Cerrar sesión",
        "email": "Dirección de correo",
        "password": "Contraseña"
    }
}
```

### i18n Hook Implementation

```typescript
// hooks/useTranslation.ts
import { useRouter } from 'next/router';
import { useMemo } from 'react';

export function useTranslation(ns: string = 'common') {
    const router = useRouter();
    const { locale, defaultLocale } = router;

    const [translation, setTranslation] = useState<Record<string, any>>({});

    useMemo(() => {
        const loadTranslation = async () => {
            const data = await import(
                `@/public/locales/${locale}/${ns}.json`
            );
            setTranslation(data.default);
        };

        loadTranslation();
    }, [locale, ns]);

    const t = (key: string): string => {
        return key.split('.').reduce((obj, k) => obj?.[k], translation) || key;
    };

    return { t, locale };
}

// Usage
export function Header() {
    const { t } = useTranslation('common');

    return (
        <header>
            <h1>{t('header.title')}</h1>
            <nav>
                <a href="/">{t('header.navigation.home')}</a>
                <a href="/about">{t('header.navigation.about')}</a>
                <a href="/contact">{t('header.navigation.contact')}</a>
            </nav>
        </header>
    );
}
```

### Pluralization & Interpolation

```typescript
// utils/i18n.ts
export function pluralize(
    count: number,
    singular: string,
    plural: string
): string {
    return count === 1 ? singular : plural;
}

export function interpolate(
    text: string,
    variables: Record<string, string | number>
): string {
    return text.replace(/{{(\w+)}}/g, (_, key) =>
        String(variables[key] ?? `{{${key}}}`)
    );
}

// translations/en.json
{
    "items_count": "You have {{count}} item{{plural}}"
}

// Usage
const count = 5;
const text = t('items_count');
const message = interpolate(text, {
    count,
    plural: pluralize(count, '', 's'),
});
// Output: "You have 5 items"
```

### Language Selector Component

```typescript
// components/LanguageSelector.tsx
import { useRouter } from 'next/router';
import { useAppStore } from '@/store/app.store';

export function LanguageSelector() {
    const router = useRouter();
    const { locale } = router;

    const languages = [
        { code: 'en', name: 'English' },
        { code: 'es', name: 'Español' },
        { code: 'fr', name: 'Français' },
        { code: 'de', name: 'Deutsch' },
        { code: 'ja', name: '日本語' },
        { code: 'zh', name: '中文' },
    ];

    const handleLanguageChange = (newLocale: string) => {
        router.push(router.pathname, router.asPath, { locale: newLocale });
    };

    return (
        <select
            value={locale}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className="px-3 py-2 border rounded"
        >
            {languages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                    {lang.name}
                </option>
            ))}
        </select>
    );
}
```

## 4. ERROR HANDLING & LOGGING

### Global Error Boundary

```typescript
// components/ErrorBoundary.tsx
import React from 'react';
import { logError } from '@/lib/logging';

interface Props {
    children: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        logError(error, {
            componentStack: errorInfo.componentStack,
        });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="p-4 bg-red-100 text-red-700 rounded">
                    <h1>Something went wrong</h1>
                    <p>{this.state.error?.message}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="mt-4 px-4 py-2 bg-red-600 text-white rounded"
                    >
                        Reload Page
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
```

### Error Logging Service

```typescript
// lib/logging.ts
interface ErrorLog {
    message: string;
    stack?: string;
    context?: Record<string, any>;
    severity: 'low' | 'medium' | 'high' | 'critical';
    timestamp: string;
    userAgent: string;
}

export async function logError(
    error: Error,
    context?: Record<string, any>
) {
    const errorLog: ErrorLog = {
        message: error.message,
        stack: error.stack,
        context,
        severity: 'high',
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
    };

    // Send to monitoring service
    if (process.env.NODE_ENV === 'production') {
        await fetch('/api/logs/errors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(errorLog),
        });
    } else {
        console.error(errorLog);
    }
}

export function logInfo(message: string, context?: Record<string, any>) {
    if (process.env.NODE_ENV === 'development') {
        console.log(message, context);
    }
}
```

---

This covers advanced state management and i18n patterns!