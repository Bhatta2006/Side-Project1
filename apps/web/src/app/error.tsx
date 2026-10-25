'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { reportError } from '@/lib/report-error';
import { NAME } from '@/lib/routes';
import { SocMoment } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => { reportError('render', error); }, [error]);
  return (
    <div role="alert">
      <SocMoment mood="worried" note="oh no. that was not supposed to happen.">
        <h1 className="type-display-m">This page hit an error</h1>
        <p className="text-base text-muted-foreground">Your progress is saved, and we have been told about this error. Try again, or go back to {NAME.today}.</p>
        <div className="mt-2 flex flex-wrap justify-center gap-3">
          <Button onClick={reset}>Try again</Button>
          <Button asChild variant="outline"><Link href="/today">{NAME.today}</Link></Button>
        </div>
      </SocMoment>
    </div>
  );
}
