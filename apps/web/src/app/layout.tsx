import type { Metadata, Viewport } from 'next';
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

export const metadata: Metadata = {
  title: { default: 'Socrat', template: '%s · Socrat' },
  description: 'Learn it. Then prove it. A personal programming tutor for learning to code, interview preparation and contests.',
  robots: { index: false, follow: false },
  applicationName: 'Socrat',
  appleWebApp: { capable: true, title: 'Socrat', statusBarStyle: 'default' },
  icons: { apple: '/icons/apple-touch-icon.png' },
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
