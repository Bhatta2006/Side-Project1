'use client';

import dynamic from 'next/dynamic';
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { holdTour } from '@/lib/first-run';
import type { BillingStatus } from '@/lib/types';

// The popup, confetti and dialog load only for a learner with an unseen launch offer.
const LaunchGiftDialog = dynamic(() => import('./launch-gift'), { ssr: false });

/** Shown once to a learner who got free Plus as one of the first signups at launch. */
export function LaunchGift() {
  const [endsAt, setEndsAt] = useState<number | null>(null);
  const release = useRef<(() => void) | null>(null);

  // The first-run tour waits until we know there is no offer, or until it is closed.
  useEffect(() => {
    const done = holdTour();
    release.current = done;
    api.get<BillingStatus>('/billing/status')
      .then(s => {
        if (!s.promo || s.promo.seen) return done();
        setEndsAt(s.promo.ends_at);
        // Marked seen as soon as it shows, so a reload does not throw the party twice.
        api.post('/billing/promo/seen').catch(() => undefined);
      })
      .catch(done);
    return done;
  }, []);

  if (endsAt === null) return null;
  return <LaunchGiftDialog endsAt={endsAt} onClose={() => release.current?.()} />;
}
