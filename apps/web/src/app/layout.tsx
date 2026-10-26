import type { Metadata, Viewport } from 'next';
import Script from 'next/script';
import localFont from 'next/font/local';
import { GeistSans } from 'geist/font/sans';
import './globals.css';
import { SessionProvider } from '@/lib/session';
import { PaywallHost } from '@/components/paywall-host';
import { REDUCE_MOTION_SCRIPT } from '@/lib/motion';
import Shell from '@/components/shell';
import { ThemeProvider } from '@/components/theme-provider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import { WebVitals } from '@/components/web-vitals';
import { ErrorReporter } from '@/components/error-reporter';
import { PwaSetup } from '@/components/install-app';
import { LEGAL } from '@/lib/legal';

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || 'G-F12E455TW1';

// Geist Sans sets everything, display and body. Handwritten margin notes use Delicious Handrawn
// (SIL OFL 1.1, vendored in src/fonts), only for asides.
const delicious = localFont({
  src: '../fonts/delicious-handrawn-latin-400.woff2',
  variable: '--font-delicious',
  weight: '400',
  display: 'swap',
});
const jetbrains = localFont({
  src: '../fonts/jetbrains-mono-latin-wght.woff2',
  variable: '--font-jetbrains',
  weight: '100 800',
  display: 'swap',
  preload: false,
});

const DESCRIPTION = 'Learn it. Then prove it. A personal programming tutor for learning to code, interview preparation and contests.';

export const metadata: Metadata = {
  metadataBase: new URL(LEGAL.site),
  title: { default: 'Socrat: a tutor that asks before it tells', template: '%s · Socrat' },
  description: DESCRIPTION,
  // Signed-in app routes are kept out of search in robots.ts; the public pages are indexable.
  robots: { index: true, follow: true },
  applicationName: 'Socrat',
  appleWebApp: { capable: true, title: 'Socrat', statusBarStyle: 'default' },
  // Google wants a favicon in multiples of 48px, linked from the page; /favicon.ico is the fallback.
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '48x48' },
      { url: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
    ],
    shortcut: '/favicon.ico',
    apple: '/icons/apple-touch-icon.png',
  },
  openGraph: {
    type: 'website',
    siteName: 'Socrat',
    title: 'Socrat: a tutor that asks before it tells',
    description: DESCRIPTION,
    url: '/',
    images: [{ url: '/icons/image.png', width: 1254, height: 1254, alt: 'Socrat' }],
  },
  twitter: { card: 'summary', title: 'Socrat', description: DESCRIPTION, images: ['/icons/image.png'] },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F6F5F0' },
    { media: '(prefers-color-scheme: dark)', color: '#121318' },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${delicious.variable} ${jetbrains.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: REDUCE_MOTION_SCRIPT }} />
      </head>
      <body>
        <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
        <Script id="gtag-init" strategy="afterInteractive">{`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${GA_ID}');`}</Script>
        <WebVitals />
        <ErrorReporter />
        <PwaSetup />
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <TooltipProvider delayDuration={200}>
            <SessionProvider>
              <Shell>{children}</Shell>
              <PaywallHost />
            </SessionProvider>
            <Toaster closeButton position="bottom-right" />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
