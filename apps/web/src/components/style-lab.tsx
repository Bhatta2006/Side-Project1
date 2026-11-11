'use client';

import { useEffect, useState } from 'react';
import { Loader2, Sparkles, Trash2 } from '@/components/icons';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';

interface Style {
  name: string; learner: string; level: string; depth: string; format: string; session_minutes: number;
  tone: string; tutor: string; rigor: string; gamified: boolean; notes: string;
}
interface Preset extends Style { key: string }

function Summary({ style }: { style: Style }) {
  const facts = [style.depth, `${style.format} format`, `${style.session_minutes} min`, `${style.tone} tone`, `${style.tutor} tutor`, `${style.rigor} rigor`, style.gamified ? 'gamified' : ''].filter(Boolean);
  return (
    <div className="grid gap-2 rounded-md border p-3 text-sm">
      <p className="font-medium">{style.name}{style.learner ? <span className="font-normal text-muted-foreground"> · {style.learner}</span> : null}</p>
      <div className="flex flex-wrap gap-1.5">{facts.map(f => <Badge key={f} variant="secondary">{f}</Badge>)}</div>
      {style.notes ? <p className="text-muted-foreground">{style.notes}</p> : null}
    </div>
  );
}

/** Admin-only: try a learning style on your own tutor before it reaches learners. */
export function StyleLab() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [mine, setMine] = useState<Style | null>(null);
  const [enrolled, setEnrolled] = useState(true);
  const [wish, setWish] = useState('');
  const [preview, setPreview] = useState<{ style: Style; source: string } | null>(null);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    api.get<{ items: Preset[] }>('/admin/style/presets').then(r => setPresets(r.items)).catch(e => toast.error(explain(e)));
    api.get<{ style: Style | null; enrolled: boolean }>('/admin/style/me').then(r => { setMine(r.style); setEnrolled(r.enrolled); }).catch(e => toast.error(explain(e)));
  }, []);

  async function run(label: string, job: () => Promise<void>) {
    setBusy(label);
    try { await job(); } catch (e) { toast.error(explain(e)); } finally { setBusy(''); }
  }

  const interpret = () => run('preview', async () => setPreview(await api.post('/admin/style/interpret', { request: wish.trim() })));
  const apply = (body: object) => run('apply', async () => {
    const r = await api.put<{ style: Style }>('/admin/style/me', body);
    setMine(r.style);
    toast.success('Your tutor now teaches in this style.');
  });
  const clear = () => run('clear', async () => { await api.del('/admin/style/me'); setMine(null); toast('Back to the standard tutor.'); });

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2" className="flex items-center gap-2"><Sparkles className="size-4" /> Learning style lab</CardTitle>
        <CardDescription>Describe how you want to learn anything. The tutor on your own account switches to it; other accounts are not affected while this is being tested.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        {!enrolled ? <p className="text-sm text-muted-foreground">Enrol in a course first: the style is stored on your active enrolment.</p> : null}
        <div className="grid gap-2">
          <Textarea value={wish} onChange={e => setWish(e.target.value)} rows={2} maxLength={600} placeholder="e.g. quantum mechanics for kids under 10, taught like a game" />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" disabled={busy !== '' || wish.trim().length < 3} onClick={interpret}>{busy === 'preview' ? <Loader2 className="animate-spin" /> : null} Preview</Button>
            <Button disabled={busy !== '' || wish.trim().length < 3 || !enrolled} onClick={() => apply({ request: wish.trim() })}>Use for my tutor</Button>
          </div>
        </div>
        {preview ? <div className="grid gap-1"><Summary style={preview.style} /><p className="text-xs text-muted-foreground">Read by {preview.source === 'agent' ? 'the Stylist agent' : 'keyword rules (no model answered)'}.</p></div> : null}
        <div className="grid gap-2">
          <h3 className="text-sm font-semibold">Presets</h3>
          <div className="flex flex-wrap gap-2">
            {presets.map(p => <Button key={p.key} size="sm" variant="outline" disabled={busy !== '' || !enrolled} onClick={() => apply({ preset: p.key })}>{p.name}</Button>)}
          </div>
        </div>
        <div className="grid gap-2">
          <h3 className="text-sm font-semibold">Your tutor is using</h3>
          {mine ? <Summary style={mine} /> : <p className="text-sm text-muted-foreground">The standard tutor.</p>}
          {mine ? <div><Button size="sm" variant="ghost" disabled={busy !== ''} onClick={clear}><Trash2 /> Back to standard</Button></div> : null}
        </div>
      </CardContent>
    </Card>
  );
}
