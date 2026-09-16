# COMPONENT ARCHITECTURE & DESIGN PATTERNS

## 1. ATOMIC DESIGN PATTERN

### Atoms - Smallest Components

```typescript
// components/ui/atoms/Button.tsx
import React from 'react';

export interface ButtonProps {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    variant?: 'primary' | 'secondary' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    type?: 'button' | 'submit' | 'reset';
    className?: string;
}

export const Button = React.forwardRef<
    HTMLButtonElement,
    ButtonProps
>(
    (
        {
            children,
            onClick,
            disabled = false,
            variant = 'primary',
            size = 'md',
            type = 'button',
            className = '',
            ...props
        },
        ref
    ) => {
        const baseStyles = 'font-semibold rounded transition-all';
        const variants = {
            primary: 'bg-blue-500 text-white hover:bg-blue-600',
            secondary: 'bg-gray-200 text-black hover:bg-gray-300',
            danger: 'bg-red-500 text-white hover:bg-red-600',
        };
        const sizes = {
            sm: 'px-2 py-1 text-sm',
            md: 'px-4 py-2 text-base',
            lg: 'px-6 py-3 text-lg',
        };

        return (
            <button
                ref={ref}
                type={type}
                onClick={onClick}
                disabled={disabled}
                className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
                {...props}
            >
                {children}
            </button>
        );
    }
);

Button.displayName = 'Button';
```

### Molecules - Combinations of Atoms

```typescript
// components/ui/molecules/FormField.tsx
import { Input } from '@/components/ui/atoms/Input';
import { Label } from '@/components/ui/atoms/Label';

export interface FormFieldProps {
    label: string;
    name: string;
    error?: string;
    required?: boolean;
    type?: string;
    placeholder?: string;
    value?: string;
    onChange?: (value: string) => void;
}

export function FormField({
    label,
    name,
    error,
    required,
    type = 'text',
    placeholder,
    value,
    onChange,
}: FormFieldProps) {
    return (
        <div className="mb-4">
            <Label htmlFor={name}>
                {label}
                {required && <span className="text-red-500">*</span>}
            </Label>
            <Input
                id={name}
                name={name}
                type={type}
                placeholder={placeholder}
                value={value}
                onChange={(e) => onChange?.(e.target.value)}
                aria-describedby={error ? `${name}-error` : undefined}
                className={error ? 'border-red-500' : ''}
            />
            {error && (
                <span id={`${name}-error`} className="text-red-500 text-sm mt-1">
                    {error}
                </span>
            )}
        </div>
    );
}
```

### Organisms - Complete Features

```typescript
// components/ui/organisms/LoginForm.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FormField } from '@/components/ui/molecules/FormField';
import { Button } from '@/components/ui/atoms/Button';
import { validateInput, schemas } from '@/lib/security/validation';

export function LoginForm() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [isLoading, setIsLoading] = useState(false);

    const handleChange = (field: string, value: string) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
        // Clear error for this field
        setErrors((prev) => ({ ...prev, [field]: '' }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        // Validate inputs
        const emailValidation = validateInput(formData.email, schemas.email);
        const passwordValidation = validateInput(
            formData.password,
            schemas.password
        );

        if (!emailValidation.valid || !passwordValidation.valid) {
            setErrors({
                email: emailValidation.error || '',
                password: passwordValidation.error || '',
            });
            setIsLoading(false);
            return;
        }

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
                credentials: 'include',
            });

            if (!res.ok) {
                const error = await res.json();
                setErrors({ submit: error.message });
                return;
            }

            router.push('/dashboard');
        } catch (error) {
            setErrors({ submit: 'Network error. Please try again.' });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="max-w-md mx-auto">
            <FormField
                label="Email"
                name="email"
                type="email"
                value={formData.email}
                onChange={(value) => handleChange('email', value)}
                error={errors.email}
                required
            />
            <FormField
                label="Password"
                name="password"
                type="password"
                value={formData.password}
                onChange={(value) => handleChange('password', value)}
                error={errors.password}
                required
            />
            {errors.submit && (
                <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
                    {errors.submit}
                </div>
            )}
            <Button
                type="submit"
                disabled={isLoading}
                className="w-full"
            >
                {isLoading ? 'Logging in...' : 'Login'}
            </Button>
        </form>
    );
}
```

## 2. CONTAINER & PRESENTATION PATTERN

### Presentation Component

```typescript
// components/UserList.presentation.tsx
export interface User {
    id: string;
    name: string;
    email: string;
    role: string;
}

export interface UserListProps {
    users: User[];
    isLoading: boolean;
    error?: string;
    onEdit: (user: User) => void;
    onDelete: (userId: string) => void;
}

export function UserListPresentation({
    users,
    isLoading,
    error,
    onEdit,
    onDelete,
}: UserListProps) {
    if (isLoading) return <div className="p-4">Loading...</div>;
    if (error) return <div className="p-4 text-red-500">{error}</div>;
    if (users.length === 0) return <div className="p-4">No users found</div>;

    return (
        <table className="w-full border-collapse border">
            <thead>
                <tr className="bg-gray-100">
                    <th className="border p-2">Name</th>
                    <th className="border p-2">Email</th>
                    <th className="border p-2">Role</th>
                    <th className="border p-2">Actions</th>
                </tr>
            </thead>
            <tbody>
                {users.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50">
                        <td className="border p-2">{user.name}</td>
                        <td className="border p-2">{user.email}</td>
                        <td className="border p-2">{user.role}</td>
                        <td className="border p-2 space-x-2">
                            <button
                                onClick={() => onEdit(user)}
                                className="text-blue-500 hover:underline"
                            >
                                Edit
                            </button>
                            <button
                                onClick={() => onDelete(user.id)}
                                className="text-red-500 hover:underline"
                            >
                                Delete
                            </button>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
```

### Container Component

```typescript
// components/UserList.container.tsx
'use client';

import { useState, useEffect } from 'react';
import { UserListPresentation } from './UserList.presentation';

export function UserListContainer() {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | undefined>();

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            setIsLoading(true);
            const res = await fetch('/api/users');
            if (!res.ok) throw new Error('Failed to fetch users');
            const data = await res.json();
            setUsers(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setIsLoading(false);
        }
    };

    const handleEdit = (user: typeof users[0]) => {
        // Navigate to edit page
        window.location.href = `/users/${user.id}/edit`;
    };

    const handleDelete = async (userId: string) => {
        if (!confirm('Are you sure?')) return;
        
        try {
            const res = await fetch(`/api/users/${userId}`, {
                method: 'DELETE',
            });
            if (!res.ok) throw new Error('Failed to delete user');
            setUsers(users.filter((u) => u.id !== userId));
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        }
    };

    return (
        <UserListPresentation
            users={users}
            isLoading={isLoading}
            error={error}
            onEdit={handleEdit}
            onDelete={handleDelete}
        />
    );
}
```

## 3. RENDER PROPS PATTERN

```typescript
// components/patterns/WithDataFetching.tsx
interface RenderProps<T> {
    data: T | null;
    loading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
}

interface WithDataFetchingProps<T> {
    url: string;
    children: (props: RenderProps<T>) => React.ReactNode;
}

export function WithDataFetching<T>({
    url,
    children,
}: WithDataFetchingProps<T>) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const res = await fetch(url);
            if (!res.ok) throw new Error('Fetch failed');
            const json = await res.json();
            setData(json);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Unknown error'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [url]);

    return (
        <>
            {children({
                data,
                loading,
                error,
                refetch: fetchData,
            })}
        </>
    );
}

// Usage
<WithDataFetching url="/api/users">
    {({ data, loading, error, refetch }) => (
        <>
            {loading && <div>Loading...</div>}
            {error && <div>Error: {error.message}</div>}
            {data && <div>{JSON.stringify(data)}</div>}
            <button onClick={refetch}>Refresh</button>
        </>
    )}
</WithDataFetching>
```

## 4. CUSTOM HOOKS PATTERNS

### Data Fetching Hook

```typescript
// hooks/useFetch.ts
interface UseFetchOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    body?: Record<string, any>;
    dependencies?: unknown[];
    skip?: boolean;
}

interface UseFetchResult<T> {
    data: T | null;
    loading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
}

export function useFetch<T>(
    url: string,
    options: UseFetchOptions = {}
): UseFetchResult<T> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(!options.skip);
    const [error, setError] = useState<Error | null>(null);

    const fetchData = useCallback(async () => {
        if (options.skip) return;

        try {
            setLoading(true);
            const res = await fetch(url, {
                method: options.method || 'GET',
                headers: { 'Content-Type': 'application/json' },
                body: options.body ? JSON.stringify(options.body) : undefined,
                credentials: 'include',
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setData(json);
            setError(null);
        } catch (err) {
            const errorObj = err instanceof Error ? err : new Error('Unknown error');
            setError(errorObj);
        } finally {
            setLoading(false);
        }
    }, [url, options, options.dependencies]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    return { data, loading, error, refetch: fetchData };
}
```

### Form Hook

```typescript
// hooks/useForm.ts
interface UseFormOptions<T> {
    initialValues: T;
    onSubmit: (values: T) => Promise<void>;
    validate?: (values: T) => Record<string, string>;
}

export function useForm<T extends Record<string, any>>({
    initialValues,
    onSubmit,
    validate,
}: UseFormOptions<T>) {
    const [values, setValues] = useState(initialValues);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [touched, setTouched] = useState<Record<string, boolean>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value, type, checked } = e.target;
        setValues((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
    };

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
        const { name } = e.target;
        setTouched((prev) => ({ ...prev, [name]: true }));

        if (validate) {
            const fieldErrors = validate(values);
            setErrors((prev) => ({
                ...prev,
                [name]: fieldErrors[name],
            }));
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (validate) {
            const newErrors = validate(values);
            setErrors(newErrors);
            if (Object.keys(newErrors).length > 0) return;
        }

        setIsSubmitting(true);
        try {
            await onSubmit(values);
        } finally {
            setIsSubmitting(false);
        }
    };

    return {
        values,
        errors,
        touched,
        isSubmitting,
        handleChange,
        handleBlur,
        handleSubmit,
        setValues,
    };
}
```

## 5. CONTEXT PATTERN FOR STATE MANAGEMENT

```typescript
// context/ThemeContext.tsx
import { createContext, useContext, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<Theme>('light');

    const toggleTheme = () => {
        setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return context;
}
```

This provides expert-level component architecture patterns!