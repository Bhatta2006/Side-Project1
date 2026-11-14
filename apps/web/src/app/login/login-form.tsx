'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from '@/components/icons';
import { api, explain } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import type { Features } from '@/lib/types';
import { LiveSoc } from '@/components/socrat/live-soc';
import type { SocMood } from '@/components/socrat/soc';
import { ErrorState } from '@/components/socrat/states';
import { EmailAuth } from './email-auth';
import { Wordmark } from '@/components/socrat/wordmark';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Paper } from '@/components/ui/paper';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z" />
      <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6H1.3a12 12 0 0 0 0 10.8l4-3.1z" />
      <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z" />
    </svg>
  );
}

/** The page a signed-out visitor first asked for; only same-site paths are honoured. */
/** Dev sign-in id: the readable slug, plus a hash of the exact name whenever the slug loses
 * characters (accents, other scripts, punctuation), so "日本語" and "Ελληνικά" never collide. */
async function subjectFor(display: string) {
  const slug = display.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  if (slug && display.trim().toLowerCase().replace(/\s+/g, '-') === slug) return slug.slice(0, 64);
  const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(display.normalize('NFKC'))));
  const hash = Array.from(bytes.slice(0, 5), b => b.toString(16).padStart(2, '0')).join('');
  return `${(slug || 'learner').slice(0, 53)}-${hash}`;
}

function requestedPath(): string | null {
  const next = new URLSearchParams(window.location.search).get('next');
  return next && next.startsWith('/') && !next.startsWith('//') ? next : null;
}

export function LoginForm({ initialFeatures }: { initialFeatures: Features | null }) {
  const session = useSession();
  const { profile, loading, refresh } = session;
  // Sign-in options come with the HTML (fetched on the server) so the form paints at once.
  const features = initialFeatures ?? session.features;
  const router = useRouter();
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!loading && profile) router.replace(destination(profile, 'active') ?? requestedPath() ?? '/today');
  }, [loading, profile, router]);

  async function signedIn() {
    const next = await refresh();
    router.replace(destination(next, 'active') ?? requestedPath() ?? '/today');
  }

  async function devLogin(event: React.FormEvent) {
    event.preventDefault();
    const display = name.trim();
    if (!display) return;
    setBusy(true);
    setError('');
    try {
      const subject = await subjectFor(display);
      await api.post('/auth/dev-login', { subject, display_name: display });
      await signedIn();
    } catch (e) {
      setError(explain(e));
      setBusy(false);
    }
  }

  // Soc reacts to the form: curious on focus, greets you by name, thinks while signing in.
  const first = name.trim().split(/\s+/)[0]?.slice(0, 20) ?? '';
  const [mood, line]: [SocMood, string | null] = error ? ['worried', 'Hmm. That did not work. Shall we try again?']
    : busy ? ['thinking', 'Looking for your notebook…']
      : first ? ['happy', `Nice to meet you, ${first}!`]
        : focused ? ['curious', 'And who might you be?']
          : ['neutral', null];

  return (
    <div className="login-page ll-desk min-h-dvh px-5 py-4 [--margin-x:20px] sm:px-8 sm:[--margin-x:40px] lg:px-10 lg:py-6 lg:[--margin-x:88px]">
      <div className="mx-auto mb-6 flex max-w-[1400px] items-center justify-between gap-4 pl-5 sm:pl-8 lg:mb-4 lg:pl-[108px]">
        <Link href="/" aria-label="Socrat home" className="rounded-full"><Wordmark /></Link>
        <Link href="/" className="inline-flex min-h-11 items-center gap-2 rounded-full px-2 text-[15px] font-medium text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" aria-hidden="true" /> Back to home
        </Link>
      </div>

      <div className="mx-auto grid max-w-[1400px] items-center gap-10 pl-5 sm:pl-8 lg:min-h-[calc(100dvh-120px)] lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:pl-[108px]">
        <section aria-labelledby="login-story-title" className="relative order-last flex flex-col gap-6 lg:order-none">
          <h2 id="login-story-title" className="font-script text-[52px] leading-[1.02] sm:text-[64px] lg:text-[88px]">Learn it.<br /><span className="hl hl-draw">Then prove it.</span></h2>
          <p className="max-w-sm text-[17px] text-muted-foreground">A tutor that asks before it tells. A plan that follows your evidence.</p>
          <div className="relative mt-2 hidden w-[260px] lg:block">
            <LiveSoc mood={mood} say={line} bubbleSide="right" />
          </div>
          <p className="font-script hidden -rotate-3 text-[26px] text-red lg:block">psst, the first question is on me ↗</p>
        </section>

        <Paper as="section" stock="paper" tape="top" seed="login-panel" className="login-panel flex flex-col justify-center p-6 sm:p-8 lg:p-12" aria-labelledby="login-title">
          <div className="mx-auto w-full max-w-md">
            <h1 id="login-title" className="type-display-l">Log in</h1>
            <p className="mt-3 text-base text-muted-foreground">{features?.email_login ? 'Log in, or create an account with Google or your email.' : 'New to Socrat? Logging in creates your account.'}</p>
            <div className="mt-6 flex items-center gap-3 lg:hidden"><LiveSoc books={false} size={64} mood={mood} say={null} className="w-16" /><p className="font-hand text-[22px] text-pen">{line ?? 'hello there!'}</p></div>

            <div className="mt-8 grid gap-4">
              {/* Sign-in options appear once the server says which are enabled. */}
              {!features ? (
                <div className="grid gap-4" role="status" aria-label="Loading sign-in options">
                  <Skeleton className="h-13 w-full rounded-full" />
                  <Skeleton className="h-40 w-full rounded-card" />
                </div>
              ) : null}
              {features?.oidc_login ? (
                <Button asChild variant="outline" size="lg" className="w-full">
                  <a href="/api/v1/auth/login"><GoogleMark /> Continue with Google</a>
                </Button>
              ) : null}
              {features?.email_login ? (
                <>
                  {features.oidc_login ? <p className="flex items-center gap-3 text-[13px] text-muted-foreground before:h-px before:flex-1 before:bg-border after:h-px after:flex-1 after:bg-border">or</p> : null}
                  <EmailAuth onSignedIn={signedIn} onBusy={setBusy} />
                </>
              ) : null}
              {features ? (
                <p className="text-center text-[13px] text-muted-foreground">
                  By continuing you agree to the <a href="/terms" className="underline underline-offset-4">terms of service</a> and the{' '}
                  <a href="/privacy" className="underline underline-offset-4">privacy policy</a>. You must be 13 or older.
                </p>
              ) : null}
              {features?.dev_login ? (
                <form onSubmit={devLogin} className="grid gap-4 rounded-[4px] border border-dashed border-border-strong p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">Simulated learner</p>
                    <span className="font-hand text-[19px] text-pen">development only</span>
                  </div>
                  <div className="grid gap-2">
                    <label htmlFor="login-name" className="text-[15px] font-medium">Your name</label>
                    <Input id="login-name" value={name} onChange={e => { setName(e.target.value); setError(''); }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} maxLength={80} autoComplete="given-name" aria-describedby="login-name-help" required autoFocus />
                    <p id="login-name-help" className="text-sm text-muted-foreground">This simulates a learner on a local build. The same name returns you to the same account.</p>
                  </div>
                  <Button size="lg" disabled={busy || !name.trim()} aria-busy={busy}>
                    {busy ? 'Logging in' : 'Log in'}<ArrowCircle loading={busy} />
                  </Button>
                  {!name.trim() ? <p className="text-[13px] text-muted-foreground">Enter a name to continue.</p> : null}
                </form>
              ) : null}
              {features && !features.oidc_login && !features.dev_login && !features.email_login ? (
                <p className="text-[15px] text-muted-foreground">Sign-in is not configured on this server.</p>
              ) : null}
              {error ? <ErrorState title="Could not log in" message={error} /> : null}
            </div>
            <p className="mt-8 text-sm text-muted-foreground">Socrat stores your learning data to plan your practice. You can export or delete it in Settings at any time.</p>
          </div>
        </Paper>
      </div>
    </div>
  );
}
