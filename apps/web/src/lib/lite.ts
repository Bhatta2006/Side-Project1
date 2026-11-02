'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSession } from '@/lib/session';

/**
 * Lite mode: spend less data on slow or metered connections. Nothing is removed; heavy parts
 * (browser code runtimes, interactive plots, simulations) wait until the learner asks for them.
 * The choice is per device, because bandwidth belongs to the device, not the account.
 * Off entirely unless the server flag `lite_mode` is on.
 */
const KEY = 'socrat:data-use';

export type DataUse = 'auto' | 'lite' | 'full';
export const DATA_USE: DataUse[] = ['auto', 'lite', 'full'];

type Connection = { saveData?: boolean; effectiveType?: string; addEventListener?: (type: 'change', fn: () => void) => void; removeEventListener?: (type: 'change', fn: () => void) => void };

function connection(): Connection | undefined {
  if (typeof navigator === 'undefined') return undefined;
  return (navigator as Navigator & { connection?: Connection }).connection;
}

/** The browser says data is precious: Data Saver is on, or the connection is 2G or slower. */
export function slowConnection(): boolean {
  const c = connection();
  if (!c) return false;
  return c.saveData === true || c.effectiveType === 'slow-2g' || c.effectiveType === '2g';
}

function stored(): DataUse {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'lite' || value === 'full' ? value : 'auto';
  } catch {
    return 'auto';
  }
}

/** Whether lite mode applies now, and the learner's choice for this device. */
export function useLite(): { available: boolean; setting: DataUse; slow: boolean; lite: boolean; set(value: DataUse): void } {
  const { features } = useSession();
  const available = features?.lite_mode === true;
  const [setting, setSetting] = useState<DataUse>('auto');
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    setSetting(stored());
    setSlow(slowConnection());
    const c = connection();
    const update = () => setSlow(slowConnection());
    c?.addEventListener?.('change', update);
    return () => c?.removeEventListener?.('change', update);
  }, []);
  const set = useCallback((value: DataUse) => {
    setSetting(value);
    try { localStorage.setItem(KEY, value); } catch { /* per-device nicety only */ }
  }, []);
  const lite = available && (setting === 'lite' || (setting === 'auto' && slow));
  return { available, setting, slow, lite, set };
}
