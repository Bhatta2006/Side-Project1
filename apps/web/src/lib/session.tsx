'use client';

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api, clearApiCache, setCsrf } from './api';
import { prefetchRoute } from './prefetch';
import type { Features, Profile } from './types';

interface SessionValue {
  profile: Profile | null;
  features: Features | null;
  loading: boolean;
  refresh(): Promise<Profile | null>;
  signOut(): Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [features, setFeatures] = useState<Features | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const status = await api.get<{ profile: Profile | null }>('/auth/status').catch(() => ({ profile: null }));
    setProfile(status.profile);
    setCsrf(status.profile?.csrf_token ?? '');
    return status.profile;
  }, []);

  useEffect(() => {
    // The page's own data and the billing status (sidebar, paywall, plan locks) start now, next to
    // the session check, instead of after it: one round trip less before a signed-in page shows.
    prefetchRoute(window.location.pathname);
    api.prefetch('/billing/status');
    Promise.all([refresh(), api.get<Features>('/features').then(setFeatures).catch(() => undefined)]).finally(() =>
      setLoading(false),
    );
  }, [refresh]);

  const signOut = useCallback(async () => {
    await api.post('/auth/logout').catch(() => undefined);
    setProfile(null);
    setCsrf('');
    clearApiCache();
    // Drafts (onboarding name, answers) belong to the learner who signed out, not the next one.
    try { sessionStorage.clear(); } catch { /* storage unavailable */ }
  }, []);

  return (
    <SessionContext.Provider value={{ profile, features, loading, refresh, signOut }}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error('useSession outside SessionProvider');
  return value;
}

export type Requirement = 'signed-in' | 'enrolled' | 'active';

/** Where a learner belongs given what a page requires; null when they may stay. */
export function destination(profile: Profile | null, need: Requirement): string | null {
  if (!profile) return '/login';
  if (need === 'signed-in') return null;
  if (!profile.enrollment) return '/start';
  if (need === 'enrolled') return null;
  if (profile.enrollment.status !== 'active') return '/placement';
  return null;
}

/** Redirects away from pages the learner cannot use yet; returns true once allowed. */
export function useGuard(need: Requirement): boolean {
  const { profile, loading } = useSession();
  const router = useRouter();
  const target = loading ? null : destination(profile, need);
  useEffect(() => {
    // Signed-out visitors come back to the page they asked for after logging in.
    if (target) router.replace(target === '/login' ? `/login?next=${encodeURIComponent(location.pathname + location.search)}` : target);
  }, [target, router]);
  return !loading && !target;
}
