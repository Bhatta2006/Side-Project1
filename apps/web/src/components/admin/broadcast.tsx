'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { ErrorNote } from '@/components/common';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, field } from '@/components/admin/ui';
import { Button } from '@/components/ui/button';

/** One note to every account. A note to a single learner is sent from their account. */
export function Broadcast() {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function send() {
    if (!window.confirm('Send this note to every account?')) return;
    setBusy(true);
    setError('');
    try {
      const { sent } = await api.post<{ sent: number }>('/admin/notifications/broadcast', { title: title.trim(), body: body.trim() });
      toast.success(`Sent to ${sent} ${sent === 1 ? 'account' : 'accounts'}.`);
      setTitle('');
      setBody('');
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Message everyone</CardTitle>
        <CardDescription>Each learner sees it once, the next time they open the app. To write to one person, open their account under Accounts.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        <input className={field} value={title} onChange={e => setTitle(e.target.value)} maxLength={120} placeholder="Title (optional)" aria-label="Title" />
        <textarea className={`${field} h-32 py-2`} value={body} onChange={e => setBody(e.target.value)} maxLength={2000} placeholder="Your message" aria-label="Message" />
        {error ? <ErrorNote message={error} /> : null}
        <div><Button disabled={!body.trim() || busy} onClick={() => void send()}>Send to everyone</Button></div>
      </CardContent>
    </Card>
  );
}
