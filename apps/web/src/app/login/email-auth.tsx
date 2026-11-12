'use client';

import { useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { ErrorState, SuccessLine } from '@/components/socrat/states';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Step = 'login' | 'signup' | 'verify' | 'forgot' | 'reset';
const RESEND_SECONDS = 60;

/**
 * Email and password: log in, create an account (confirmed by an emailed code), or reset a
 * forgotten password (also by code). `onSignedIn` runs once the server has set the session.
 */
export function EmailAuth({ onSignedIn, onBusy }: { onSignedIn: () => Promise<void>; onBusy?: (busy: boolean) => void }) {
  const [step, setStep] = useState<Step>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (!wait) return;
    const timer = setTimeout(() => setWait(w => w - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  function go(next: Step) { setStep(next); setError(''); setNotice(''); setCode(''); }

  async function run(action: () => Promise<void>) {
    setBusy(true); onBusy?.(true); setError('');
    try { await action(); }
    catch (e) { setError(explain(e)); }
    finally { setBusy(false); onBusy?.(false); }
  }

  const sendSignup = () => run(async () => {
    await api.post('/auth/email/signup', { email, password, display_name: name.trim() });
    setStep('verify'); setCode(''); setWait(RESEND_SECONDS);
    setNotice(`If ${email.trim()} can receive email, a 6-digit code is on its way.`);
  });
  const sendReset = () => run(async () => {
    await api.post('/auth/email/reset', { email });
    setStep('reset'); setCode(''); setPassword(''); setWait(RESEND_SECONDS);
    setNotice(`If ${email.trim()} has a Socrat account, a 6-digit code is on its way.`);
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (step === 'login') void run(async () => { await api.post('/auth/email/login', { email, password }); await onSignedIn(); });
    else if (step === 'signup') void sendSignup();
    else if (step === 'verify') void run(async () => { await api.post('/auth/email/verify', { email, code }); await onSignedIn(); });
    else if (step === 'forgot') void sendReset();
    else void run(async () => { await api.post('/auth/email/reset/confirm', { email, code, password }); await onSignedIn(); });
  }

  const needsCode = step === 'verify' || step === 'reset';
  const needsPassword = step === 'login' || step === 'signup' || step === 'reset';
  const newPassword = step === 'signup' || step === 'reset';
  const ready = email.trim().length > 3
    && (!needsPassword || password.length >= (newPassword ? 8 : 1))
    && (!needsCode || /^\d{6}$/.test(code));
  const title = { login: 'Log in with email', signup: 'Create an account', verify: 'Check your email', forgot: 'Reset your password', reset: 'Choose a new password' }[step];
  const action = { login: 'Log in', signup: 'Send code', verify: 'Create account', forgot: 'Send code', reset: 'Save and log in' }[step];

  return (
    <form onSubmit={submit} className="grid gap-4" aria-labelledby="email-auth-title" noValidate>
      <h2 id="email-auth-title" className="font-medium">{title}</h2>
      {notice ? <SuccessLine>{notice}</SuccessLine> : null}

      {step === 'signup' ? (
        <div className="grid gap-2">
          <label htmlFor="email-name" className="text-[15px] font-medium">Your name <span className="font-normal text-muted-foreground">(optional)</span></label>
          <Input id="email-name" value={name} onChange={e => setName(e.target.value)} maxLength={80} autoComplete="given-name" />
        </div>
      ) : null}
      <div className="grid gap-2">
        <label htmlFor="email-address" className="text-[15px] font-medium">Email</label>
        <Input id="email-address" type="email" value={email} onChange={e => { setEmail(e.target.value); setError(''); }} maxLength={254} autoComplete="email" inputMode="email" readOnly={needsCode} required />
      </div>
      {needsCode ? (
        <div className="grid gap-2">
          <label htmlFor="email-code" className="text-[15px] font-medium">6-digit code</label>
          <Input id="email-code" value={code} onChange={e => { setCode(e.target.value.replace(/\D/g, '').slice(0, 6)); setError(''); }} inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" className="tracking-[0.3em] tabular-nums" required autoFocus aria-describedby="email-code-help" />
          <p id="email-code-help" className="text-sm text-muted-foreground">
            The code expires in 10 minutes.{' '}
            <button type="button" className="font-medium underline underline-offset-4 disabled:no-underline disabled:opacity-60" disabled={busy || wait > 0} onClick={() => void (step === 'verify' ? sendSignup() : sendReset())}>
              {wait > 0 ? `Send a new code in ${wait}s` : 'Send a new code'}
            </button>
          </p>
        </div>
      ) : null}
      {needsPassword ? (
        <div className="grid gap-2">
          <div className="flex items-center justify-between gap-3">
            <label htmlFor="email-password" className="text-[15px] font-medium">{newPassword ? 'New password' : 'Password'}</label>
            {step === 'login' ? <button type="button" className="text-sm font-medium underline underline-offset-4" onClick={() => go('forgot')}>Forgot password?</button> : null}
          </div>
          <Input id="email-password" type="password" value={password} onChange={e => { setPassword(e.target.value); setError(''); }} maxLength={128} autoComplete={newPassword ? 'new-password' : 'current-password'} aria-describedby={newPassword ? 'email-password-help' : undefined} required />
          {newPassword ? <p id="email-password-help" className="text-sm text-muted-foreground">At least 8 characters. A short phrase is easy to remember and hard to guess.</p> : null}
        </div>
      ) : null}

      <Button size="lg" disabled={busy || !ready} aria-busy={busy}>
        {busy ? 'Please wait' : action}<ArrowCircle loading={busy} />
      </Button>
      {error ? <ErrorState title="That did not work" message={error} /> : null}

      <p className="text-[15px] text-muted-foreground">
        {step === 'login' ? <>New to Socrat? <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={() => go('signup')}>Create an account</button></>
          : step === 'verify' ? <>Wrong email? <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={() => go('signup')}>Start again</button></>
            : <>Remembered it? <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={() => go('login')}>Log in</button></>}
      </p>
    </form>
  );
}
