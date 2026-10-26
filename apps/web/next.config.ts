import type { NextConfig } from 'next';

const config: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  // The floating dev badge overlaps the sidebar and tutor button.
  devIndicators: false,
  // Generation, browser checking, content review and repairs have a five-minute server budget.
  experimental: { proxyTimeout: 330_000 },
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/:path*` }];
  },
  async headers() {
    const common = [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'Referrer-Policy', value: 'same-origin' },
      { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
    ];
    return [
      // Everything except the code-runner workers, which carry their own policy below.
      { source: '/((?!runner/).*)', headers: [
        ...common,
        { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self' 'unsafe-inline' https://checkout.razorpay.com https://www.googletagmanager.com" + (process.env.NODE_ENV === 'development' ? " 'unsafe-eval'" : '') + "; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.razorpay.com https://*.google-analytics.com https://*.googletagmanager.com; connect-src 'self' https://api.razorpay.com https://lumberjack.razorpay.com https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com; worker-src 'self'; font-src 'self'; frame-src https://api.razorpay.com " + (process.env.NEXT_PUBLIC_EXPLAINER_SANDBOX_ORIGIN || 'http://127.0.0.1:8000') + "; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'" },
      ] },
      // Workers compile WebAssembly, and Pyodide evaluates generated glue code. They have no
      // DOM; the page's own policy is unchanged.
      { source: '/runner/:path*', headers: [
        ...common,
        { key: 'Content-Security-Policy', value: "default-src 'none'; script-src 'self' 'wasm-unsafe-eval' 'unsafe-eval'; connect-src 'self'" },
        { key: 'Cache-Control', value: 'public, max-age=3600' },
      ] },
      // The service worker must be re-checked on every load so updates ship promptly.
      { source: '/sw.js', headers: [
        { key: 'Cache-Control', value: 'no-cache' },
        { key: 'Service-Worker-Allowed', value: '/' },
      ] },
      // Runtime files live under versioned directories, so they never change in place.
      { source: '/runtimes/:name/:file+', headers: [
        { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
      ] },
    ];
  },
};
export default config;
