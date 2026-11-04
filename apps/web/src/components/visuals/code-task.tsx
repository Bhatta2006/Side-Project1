'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

/**
 * A coding task in a lesson. With a judged problem it opens the real judged page (where evidence
 * is recorded). Without one it is free practice: a starter to copy, clearly not judged. The
 * browser editor is not embedded here, so nothing on this card claims to run or grade code.
 */
export function CodeTask({ params }: { params: { language: string; starter?: string; problem_id?: string | null } }) {
  const [copied, setCopied] = useState(false);
  const starter = params.starter ?? '';
  return (
    <div className="grid gap-3 text-sm">
      {params.problem_id ? (
        <p>
          <Button asChild size="sm"><Link href={`/problems/${params.problem_id}`}>Open the judged problem</Link></Button>
          <span className="ml-3 text-muted-foreground">It runs your {params.language} code against hidden tests.</span>
        </p>
      ) : (
        <p className="text-muted-foreground">Free practice in {params.language}: not judged, and it does not count as evidence.</p>
      )}
      {starter ? (
        <>
          <pre className="overflow-x-auto rounded-lg border bg-background p-3 text-[13px]"><code>{starter}</code></pre>
          <div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => { void navigator.clipboard?.writeText(starter).then(() => setCopied(true)).catch(() => undefined); }}
            >
              {copied ? 'Copied' : 'Copy starter'}
            </Button>
          </div>
        </>
      ) : null}
    </div>
  );
}
