'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, api, explain } from '@/lib/api';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { Pill } from '@/components/choice';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Group = { id: string; single: boolean; choices: { id: string; label: string }[] };
type Options = { subjects: { id: string; label: string; group: string }[]; groups: Group[] };
type Concept = { id: string; title: string; prerequisites: string[]; status: string; objectives: string[] };
type Intent = {
  subject: string;
  goal: string;
  desired_level: string;
  starting_level: string;
  register: string;
  clarifications: string[];
  blocked: string;
  safety_notes: string[];
  needs_physical_practice: boolean;
  needs_external_evaluator: boolean;
  verifiable: string;
};
type LearningRequest = {
  id: string;
  status: 'parsed' | 'needs_clarification' | 'blocked' | 'confirmed';
  source: 'model' | 'rules';
  intent: Intent;
  course_id: string | null;
  published: boolean;
  job: { state: string; error: string } | null;
  blueprint: { title: string; tagline: string; modules: { id: string; title: string; concepts: Concept[] }[] } | null;
  enroll: Record<string, unknown> | null;
};

const GROUP_TITLE: Record<string, string> = {
  who: 'Who is learning?',
  level: 'How far do you want to go?',
  style: 'How do you like to learn?',
  time: 'How much time a day?',
};

export default function NewCourse() {
  const router = useRouter();
  const [options, setOptions] = useState<Options | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [text, setText] = useState('');
  const [picks, setPicks] = useState<string[]>([]);
  const [req, setReq] = useState<LearningRequest | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<Options>('/learning-requests/options')
      .then(setOptions)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) setUnavailable(true);
        else setError(explain(e));
      });
  }, []);

  // While the plan is being written, ask again every few seconds until it is ready or failed.
  const waiting = req?.status === 'confirmed' && !req.blueprint && req.job?.state !== 'failed';
  useEffect(() => {
    if (!waiting || !req) return;
    const timer = setInterval(() => {
      api.get<LearningRequest>(`/learning-requests/${req.id}`).then(setReq).catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [waiting, req]);

  function toggle(group: Group, id: string) {
    setPicks((current) => {
      if (current.includes(id)) return current.filter((p) => p !== id);
      const kept = group.single ? current.filter((p) => !group.choices.some((c) => c.id === p)) : current;
      return [...kept, id];
    });
  }

  async function run<T>(work: () => Promise<T>, done: (value: T) => void) {
    setBusy(true);
    setError('');
    try {
      done(await work());
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  const make = () => run(() => api.post<LearningRequest>('/learning-requests', { text, choices: picks }), setReq);
  const confirm = () => {
    if (req) run(() => api.post<LearningRequest>(`/learning-requests/${req.id}/confirm`, {}), setReq);
  };
  const start = () => {
    if (!req) return;
    run(
      async () => {
        const published = await api.post<LearningRequest>(`/learning-requests/${req.id}/publish`, {});
        await api.post('/enrollments', published.enroll);
      },
      () => router.push('/today'),
    );
  };

  if (unavailable) {
    return (
      <Page narrow>
        <PageHeader title="Build your own course" description="This is not open to your account yet." />
      </Page>
    );
  }
  if (!options) {
    return error ? (
      <Page narrow>
        <ErrorNote message={error} />
      </Page>
    ) : (
      <Loading />
    );
  }

  const intent = req?.intent;
  return (
    <Page narrow>
      <PageHeader
        eyebrow="your course"
        title="What do you want to learn?"
        description="Type anything, or start from a suggestion. Then tell Socrat who is learning and how."
      />

      {!req ? (
        <div className="space-y-8">
          <div>
            <label htmlFor="subject" className="mb-2 block font-semibold">
              Your subject
            </label>
            <Input
              id="subject"
              value={text}
              maxLength={500}
              onChange={(e) => setText(e.target.value)}
              placeholder="For example: how black holes work, Carnatic music, circuits"
            />
            <ul className="mt-3 flex flex-wrap gap-2" aria-label="Suggested subjects">
              {options.subjects.map((s) => (
                <li key={s.id}>
                  <Pill pressed={text === s.label} onClick={() => setText(s.label)}>
                    {s.label}
                  </Pill>
                </li>
              ))}
            </ul>
          </div>
          {options.groups.map((group) => (
            <fieldset key={group.id}>
              <legend className="mb-2 font-semibold">{GROUP_TITLE[group.id] ?? group.id}</legend>
              <div className="flex flex-wrap gap-2">
                {group.choices.map((c) => (
                  <Pill key={c.id} pressed={picks.includes(c.id)} onClick={() => toggle(group, c.id)}>
                    {c.label}
                  </Pill>
                ))}
              </div>
            </fieldset>
          ))}
          {error ? <ErrorNote message={error} /> : null}
          <Button onClick={make} disabled={busy || text.trim().length < 3}>
            {busy ? 'Reading your request…' : 'Make my plan'}
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {req.status === 'blocked' ? <ErrorNote message="Socrat can't build a course for that request." /> : null}
          {intent ? (
            <section className="rounded-[20px] border bg-card p-5" aria-label="What Socrat understood">
              <h2 className="font-semibold">What Socrat understood</h2>
              <p className="mt-2">
                {intent.subject}: {intent.goal}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                From {intent.starting_level} to {intent.desired_level}, written for: {intent.register}.
                {req.source === 'rules' ? ' (Read with simple rules; the AI reader was not available.)' : ''}
              </p>
              {intent.needs_physical_practice || intent.needs_external_evaluator ? (
                <p className="mt-2 text-sm">
                  This skill needs real-world practice, and Socrat cannot judge a real performance by text alone.
                  Those parts will be marked as self- or expert-checked, not verified.
                </p>
              ) : null}
              {intent.safety_notes.map((n) => (
                <p key={n} className="mt-2 text-sm">
                  {n}
                </p>
              ))}
              {intent.clarifications.map((q) => (
                <p key={q} className="mt-2 text-sm font-medium">
                  {q}
                </p>
              ))}
            </section>
          ) : null}

          {waiting ? <Loading label="Writing your course plan" variant="inline" /> : null}
          {req.job?.state === 'failed' ? (
            <ErrorNote message="The plan could not be written. Try again with more detail." />
          ) : null}

          {req.blueprint ? (
            <section aria-label="Your course plan">
              <h2 className="type-display-l">{req.blueprint.title}</h2>
              <p className="mt-1 text-muted-foreground">{req.blueprint.tagline}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Lessons are written just before you reach them. You can see what comes later, and nothing is shown as
                ready until it is.
              </p>
              {req.blueprint.modules.map((m) => (
                <div key={m.id} className="mt-5">
                  <h3 className="font-semibold">{m.title}</h3>
                  <ol className="mt-2 space-y-2">
                    {m.concepts.map((c) => (
                      <li key={c.id} className="rounded-xl border bg-card px-4 py-3">
                        <p className="font-medium">{c.title}</p>
                        {c.objectives[0] ? <p className="text-sm text-muted-foreground">{c.objectives[0]}</p> : null}
                        {c.prerequisites.length ? (
                          <p className="text-[13px] text-muted-foreground">After: {c.prerequisites.join(', ')}</p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </section>
          ) : null}

          {error ? <ErrorNote message={error} /> : null}
          <div className="flex flex-wrap gap-3">
            {req.status === 'parsed' ? (
              <Button onClick={confirm} disabled={busy}>
                Looks right, write my plan
              </Button>
            ) : null}
            {req.blueprint ? (
              <Button onClick={start} disabled={busy}>
                {busy ? 'Starting…' : 'Start this course'}
              </Button>
            ) : null}
            <Button
              variant="outline"
              onClick={() => {
                setReq(null);
                setError('');
              }}
              disabled={busy}
            >
              Change my answers
            </Button>
          </div>
        </div>
      )}
    </Page>
  );
}
