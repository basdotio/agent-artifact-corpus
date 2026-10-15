import type { NextConfig } from 'next';

const basePath = process.env.NEXT_PUBLIC_BASE_PATH;

const nextConfig: NextConfig = {
  output: 'export', // SSG export for S3 + CloudFront
  images: {
    unoptimized: true, // needed for static export
  },
  // Important for S3/CloudFront folder structure
  trailingSlash: true,
  // Optional: deploy under a sub-path (e.g., /onboarding)
  ...(basePath ? { basePath } : {}),
};

export default nextConfig;
