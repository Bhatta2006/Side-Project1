'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useSession } from '@/lib/session';
import { en, type MessageKey } from './messages/en';

/**
 * Languages the interface itself is translated into. Lessons and the tutor support more (see the
 * API's /locales); a locale with no catalog here shows English menus around translated lessons.
 */
type Catalog = Partial<Record<MessageKey, string>>;
// Loaded only when chosen, so English pages never download other languages' strings.
const LOADERS: Record<string, () => Promise<Catalog>> = {
  hi: () => import('./messages/hi').then(m => m.hi),
};
const loaded: Record<string, Catalog> = { en };
const RTL = new Set(['ar']);
const STORAGE_KEY = 'socrat_locale';

export interface LocaleInfo {
  tag: string;
  name: string;
  native: string;
  rtl: boolean;
  preview: boolean;
}

interface I18n {
  locale: string;
  /** Looks a string up; English when this language lacks it. `{name}` style values are filled in. */
  t(key: MessageKey, values?: Record<string, string | number>): string;
  /** For labels whose key is built at run time: the translation if there is one, else `fallback`. */
  tx(key: string, fallback: string): string;
  /** Switches the interface at once and remembers it for signed-out visits. */
  setLocale(tag: string): void;
}

const I18nContext = createContext<I18n | null>(null);

function remembered(): string {
  try { return localStorage.getItem(STORAGE_KEY) ?? 'en'; } catch { return 'en'; }
}

export function fill(text: string, values?: Record<string, string | number>): string {
  if (!values) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name: string) => (name in values ? String(values[name]) : whole));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const { profile } = useSession();
  const [chosen, setChosen] = useState('en');
  const [ready, setReady] = useState(0);
  // Signed in: the account's language. Otherwise whatever this browser remembered.
  useEffect(() => { setChosen(profile?.locale ?? remembered()); }, [profile?.locale]);

  // The <html> tag is static so public pages stay prerendered; the language is set once known.
  useEffect(() => {
    document.documentElement.lang = chosen;
    document.documentElement.dir = RTL.has(chosen) ? 'rtl' : 'ltr';
  }, [chosen]);

  // Until a catalog arrives, missing keys show English (the same fallback as any untranslated key).
  useEffect(() => {
    const load = LOADERS[chosen];
    if (!load || loaded[chosen]) return;
    let live = true;
    load().then(catalog => { loaded[chosen] = catalog; if (live) setReady(n => n + 1); }).catch(() => undefined);
    return () => { live = false; };
  }, [chosen]);

  const setLocale = useCallback((tag: string) => {
    setChosen(tag);
    try { localStorage.setItem(STORAGE_KEY, tag); } catch { /* storage unavailable */ }
  }, []);

  const value = useMemo<I18n>(() => {
    const catalog = loaded[chosen] ?? {};
    return {
      locale: chosen,
      setLocale,
      t: (key, values) => fill(catalog[key] ?? en[key], values),
      tx: (key, fallback) => (catalog as Record<string, string>)[key] ?? fallback,
    };
  }, [chosen, ready, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const value = useContext(I18nContext);
  if (!value) throw new Error('useI18n outside I18nProvider');
  return value;
}

export type { MessageKey };
