# PERFORMANCE OPTIMIZATION & PWA

## 1. CORE WEB VITALS OPTIMIZATION

### LCP (Largest Contentful Paint)

```typescript
// lib/performance/lcp.ts
/**
 * Optimize LCP (target: < 2.5s)
 * - Optimize server response time (TTFB)
 * - Optimize critical render path
 * - Optimize images
 */

// 1. Preload critical resources
// app/layout.tsx
export default function RootLayout({ children }: any) {
    return (
        <html>
            <head>
                {/* Preload critical images */}
                <link
                    rel="preload"
                    as="image"
                    href="/hero-image.jpg"
                    imagesrcset="/hero-image-mobile.jpg 480w, /hero-image-desktop.jpg 1200w"
                />

                {/* Preload critical fonts */}
                <link
                    rel="preload"
                    as="font"
                    href="/fonts/inter.woff2"
                    type="font/woff2"
                    crossOrigin="anonymous"
                />

                {/* Preconnect to external services */}
                <link rel="preconnect" href="https://api.example.com" />
                <link rel="dns-prefetch" href="https://cdn.example.com" />
            </head>
            <body>{children}</body>
        </html>
    );
}

// 2. Optimize server response time
// app/api/critical-data/route.ts
export async function GET(req: NextRequest) {
    // Use caching headers
    const headers = {
        'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120',
    };

    // Generate response as quickly as possible
    const data = await getCachedData();
    return NextResponse.json(data, { headers });
}

// 3. Lazy load non-critical above-the-fold content
export function HeroSection() {
    return (
        <Image
            src="/hero.jpg"
            alt="Hero"
            width={1200}
            height={600}
            priority  // LCP image should have priority
            sizes="100vw"
        />
    );
}

export function BelowFoldContent() {
    return (
        <Suspense fallback={<Skeleton />}>
            <ExpensiveComponent />
        </Suspense>
    );
}
```

### FID/INP (Input Delay)

```typescript
// lib/performance/fid.ts
/**
 * Optimize FID/INP (target: < 100ms/200ms)
 * - Break up long tasks
 * - Defer non-essential code
 * - Optimize event handlers
 */

// 1. Use requestIdleCallback for non-urgent work
function deferWork(callback: () => void) {
    if ('requestIdleCallback' in window) {
        requestIdleCallback(callback);
    } else {
        setTimeout(callback, 0);
    }
}

// 2. Break long tasks into smaller chunks
async function processLargeData(data: any[]) {
    let i = 0;
    const chunkSize = 100;

    while (i < data.length) {
        const chunk = data.slice(i, i + chunkSize);
        processChunk(chunk);
        
        // Yield to browser
        await new Promise((resolve) => setTimeout(resolve, 0));
        i += chunkSize;
    }
}

// 3. Debounce event handlers
export function useDebounce<T extends (...args: any[]) => any>(
    callback: T,
    delay: number
) {
    const timeoutRef = useRef<NodeJS.Timeout>();

    return useCallback(
        (...args: Parameters<T>) => {
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
            timeoutRef.current = setTimeout(() => {
                callback(...args);
            }, delay);
        },
        [callback, delay]
    );
}

// Usage
function SearchComponent() {
    const handleSearch = useDebounce((query: string) => {
        fetchSearchResults(query);
    }, 300);

    return (
        <input
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search..."
        />
    );
}
```

### CLS (Cumulative Layout Shift)

```typescript
// lib/performance/cls.ts
/**
 * Optimize CLS (target: < 0.1)
 * - Reserve space for dynamic content
 * - Avoid inserting content above existing content
 * - Avoid animations that trigger layout changes
 */

// 1. Reserve space for images
export function ResponsiveImage({ width, height, src, alt }: any) {
    const aspectRatio = (height / width) * 100;

    return (
        <div
            style={{
                paddingBottom: `${aspectRatio}%`,
                position: 'relative',
            }}
        >
            <Image
                src={src}
                alt={alt}
                fill
                style={{ position: 'absolute' }}
            />
        </div>
    );
}

// 2. Avoid layout shifts with proper skeleton loaders
export function SkeletonLoader() {
    return (
        <div className="animate-pulse">
            <div className="h-12 bg-gray-200 rounded mb-4" />
            <div className="h-6 bg-gray-200 rounded w-3/4" />
        </div>
    );
}

// 3. Use transform instead of layout-triggering properties
// BAD: Changes layout
.expand {
    height: auto;
    width: auto;
}

// GOOD: No layout shift
.expand {
    transform: scale(1);
}

// 4. Reserve space for ads and embeds
export function AdSpace({ width = 300, height = 250 }: any) {
    return (
        <div
            style={{
                width,
                height,
                minHeight: height, // Prevents collapse before ad loads
            }}
        >
            {/* Ad content here */}
        </div>
    );
}
```

## 2. BUNDLE SIZE OPTIMIZATION

### Code Splitting

```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
    webpack: (config, { isServer }) => {
        config.optimization = {
            ...config.optimization,
            usedExports: true,
            sideEffects: false,
            splitChunks: {
                chunks: 'all',
                cacheGroups: {
                    vendor: {
                        test: /[\\/]node_modules[\\/]/,
                        name: 'vendor',
                        priority: 10,
                        reuseExistingChunk: true,
                    },
                    common: {
                        minChunks: 2,
                        priority: 5,
                        reuseExistingChunk: true,
                    },
                    react: {
                        test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
                        name: 'react-vendors',
                        priority: 15,
                    },
                },
            },
        };

        return config;
    },
};

module.exports = nextConfig;
```

### Tree Shaking

```typescript
// ES Modules for better tree shaking
// utils/math.ts
export function add(a: number, b: number) {
    return a + b;
}

export function subtract(a: number, b: number) {
    return a - b;
}

// Usage - only add is included in bundle
import { add } from '@/utils/math';

// NOT GOOD - imports everything
import * as math from '@/utils/math';

// Configure package.json for tree shaking
{
    "name": "my-lib",
    "type": "module",
    "sideEffects": false,
    "exports": {
        ".": {
            "types": "./dist/index.d.ts",
            "import": "./dist/index.js",
            "require": "./dist/index.cjs"
        }
    }
}
```

## 3. CACHING STRATEGIES

### Service Worker Caching

```typescript
// public/sw.js
const CACHE_NAME = 'v1';
const ASSETS_TO_CACHE = [
    '/',
    '/index.html',
    '/styles/main.css',
    '/scripts/main.js',
];

// Install event - cache assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.match(event.request).then((response) => {
            if (response) return response;

            return fetch(event.request).then((response) => {
                // Cache successful responses
                if (response && response.status === 200) {
                    const cloned = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, cloned);
                    });
                }
                return response;
            });
        })
    );
});
```

### Cache Headers

```typescript
// middleware.ts
export function middleware(request: NextRequest) {
    const response = NextResponse.next();

    // Cache static assets for 1 year
    if (request.nextUrl.pathname.match(/\.(js|css|png|jpg|gif|svg|woff|woff2)$/)) {
        response.headers.set(
            'Cache-Control',
            'public, max-age=31536000, immutable'
        );
    }

    // Cache HTML pages for 24 hours
    if (request.nextUrl.pathname.endsWith('.html') || request.nextUrl.pathname === '/') {
        response.headers.set(
            'Cache-Control',
            'public, max-age=86400, s-maxage=3600'
        );
    }

    // Don't cache API responses
    if (request.nextUrl.pathname.startsWith('/api/')) {
        response.headers.set(
            'Cache-Control',
            'no-store, no-cache, must-revalidate'
        );
    }

    return response;
}
```

## 4. PROGRESSIVE WEB APPS (PWA)

### manifest.json

```json
{
    "name": "My Awesome App",
    "short_name": "MyApp",
    "description": "The best PWA ever",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait-primary",
    "background_color": "#ffffff",
    "theme_color": "#000000",
    "icons": [
        {
            "src": "/icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable"
        }
    ],
    "categories": ["productivity"],
    "screenshots": [
        {
            "src": "/screenshot1.png",
            "sizes": "540x720",
            "type": "image/png",
            "form_factor": "narrow"
        }
    ],
    "shortcuts": [
        {
            "name": "Create Task",
            "short_name": "New Task",
            "description": "Create a new task",
            "url": "/task/new",
            "icons": [
                {
                    "src": "/task-icon.png",
                    "sizes": "192x192"
                }
            ]
        }
    ]
}
```

### PWA Setup in Next.js

```typescript
// next.config.js
const withPWA = require('next-pwa')({
    dest: 'public',
    disable: process.env.NODE_ENV === 'development',
    register: true,
    scope: '/',
    sw: 'service-worker.js',
});

module.exports = withPWA({
    // Next.js config
    reactStrictMode: true,
    swcMinify: true,
});

// app/layout.tsx
export default function RootLayout({ children }: any) {
    return (
        <html>
            <head>
                <link rel="manifest" href="/manifest.json" />
                <meta name="theme-color" content="#000000" />
                <meta name="apple-mobile-web-app-capable" content="yes" />
                <meta
                    name="apple-mobile-web-app-status-bar-style"
                    content="black-translucent"
                />
            </head>
            <body>{children}</body>
        </html>
    );
}
```

### Offline Support

```typescript
// hooks/useOnline.ts
export function useOnline() {
    const [isOnline, setIsOnline] = useState(true);

    useEffect(() => {
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    return isOnline;
}

// Usage
export function App() {
    const isOnline = useOnline();

    return (
        <div>
            {!isOnline && (
                <div className="fixed bottom-0 bg-yellow-500 p-4">
                    You are offline. Some features may be limited.
                </div>
            )}
            {/* App content */}
        </div>
    );
}
```

---

This covers complete performance and PWA optimization!