'use client';

import { useEffect, useState } from 'react';
import { api } from './api';
import type { BillingStatus } from './types';

/** Which topics sit outside the learner's plan. Free learners only get the first modules. */
export function usePlanLocks(): (concept: string) => boolean {
  const [free, setFree] = useState<Set<string> | null>(null);
  useEffect(() => {
    api.cached<BillingStatus>('/billing/status')
      .then(s => setFree(s.enabled && s.free_concepts ? new Set(s.free_concepts) : null))
      .catch(() => setFree(null));
  }, []);
  return concept => free !== null && !free.has(concept);
}
