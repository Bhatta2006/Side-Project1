'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, api, explain } from '@/lib/api';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { useI18n } from '@/lib/i18n';
import { Pill } from '@/components/choice';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Group = { id: string; single: boolean; choices: { id: string; label: string }[] };
type Options = { subjects: { id: string; label: string; group: string }[]; groups: Group[] };
type Concept = {
  id: string;
  title: string;
  prerequisites: string[];
  status: string;
  generation?: string;
  objectives: string[];
  minutes?: number;
  category?: 'knowledge' | 'skill' | 'both' | null;
  evidence?: string[];
  expected?: string;
};

// How you will show you have learned it, in plain words (the competency's required evidence).
const EVIDENCE: Record<string, string> = {
  recognition: 'pick the right answer',
  recall: 'remember it unaided',
  application: 'use it on a task',
  transfer: 'use it somewhere new',
  explanation: 'explain why',
  performance: 'do it, judged by a person',
};

// What the engine is doing with each lesson, in plain words. Nothing reads as ready until it is.
const STAGE: Record<string, string> = {
  planned: 'Planned',
  queued: 'Waiting to be written',
  generating: 'Being written',
  validating: 'Being checked',
  published: 'Ready',
  failed: 'Did not pass its checks',
  blocked: 'Stopped after several tries',
  cancelled: 'Stopped by you',
  superseded: 'Withdrawn, being rewritten',
};
const RETRYABLE = new Set(['failed', 'blocked', 'cancelled']);
const MOVING = new Set(['queued', 'generating', 'validating']);
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
  blueprint: {
    title: string;
    tagline: string;
    modules: { id: string; title: string; concepts: Concept[] }[];
    assumptions?: string[];
    unresolved?: string[];
  } | null;
  enroll: Record<string, unknown> | null;
  diagnostic: 'none' | 'ready' | 'done';
  ready: number;
  total: number;
  community: {
    shared: boolean;
    credit: string | null;
    learners: number;
    tiers: { id: string; learners: number; label: string; earned: boolean }[];
  } | null;
};
type Check = {
  questions: { concept: string; stem: string; options: string[] }[];
  done: boolean;
  note: string;
  result: null | {
    correct: number;
    total: number;
    level_label: string;
    review: { concept: string; correct: boolean; answer: number; why: string }[];
  };
};
type Enrolled = { id: string; course: string; title: string; active: boolean };

const GROUP_TITLE: Record<string, string> = {
  who: 'Who is learning?',
  level: 'How far do you want to go?',
  style: 'How do you like to learn?',
  time: 'How much time a day?',
};

export default function NewCourse() {
  const { t, tx } = useI18n();
  const router = useRouter();
  const [options, setOptions] = useState<Options | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [text, setText] = useState('');
  const [picks, setPicks] = useState<string[]>([]);
  const [req, setReq] = useState<LearningRequest | null>(null);
  // Every change to a published plan, and why (never silent; coursegen/evolve.py).
  const [changes, setChanges] = useState<{ version: number; change: string; reason: string }[]>([]);
  useEffect(() => {
    if (!req?.published) return;
    api.get<{ items: { version: number; change: string; reason: string }[] }>(`/learning-requests/${req.id}/revisions`)
      .then(r => setChanges(r.items)).catch(() => undefined);
  }, [req?.id, req?.published]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [consent, setConsent] = useState(false);
  const [credit, setCredit] = useState<'anonymous' | 'name'>('anonymous');
  const [mine, setMine] = useState<Enrolled[]>([]);

  useEffect(() => {
    api.get<{ items: Enrolled[] }>('/enrollments').then((r) => setMine(r.items)).catch(() => {});
  }, []);

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
  // Lessons being written in the background: keep the stages fresh until they settle.
  const writing = !!req?.blueprint?.modules.some((m) => m.concepts.some((c) => MOVING.has(c.generation ?? '')));
  useEffect(() => {
    if (!(waiting || writing) || !req) return;
    const timer = setInterval(() => {
      api.get<LearningRequest>(`/learning-requests/${req.id}`).then(setReq).catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [waiting, writing, req]);

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

  const regenerate = (concept: string) => {
    if (req) run(() => api.post<LearningRequest>(`/learning-requests/${req.id}/concepts/${concept}/regenerate`, {}), setReq);
  };
  const stopWriting = () => {
    if (req) run(() => api.post<LearningRequest>(`/learning-requests/${req.id}/cancel`, {}), setReq);
  };
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

  const [check, setCheck] = useState<Check | null>(null);
  const [picked, setPicked] = useState<(number | null)[]>([]);
  const startCheck = () => {
    if (!req) return;
    run(() => api.post<Check>(`/learning-requests/${req.id}/diagnostic`, {}), (c) => {
      setCheck(c);
      setPicked(c.questions.map(() => null));
    });
  };
  const submitCheck = () => {
    if (!req) return;
    run(
      async () => {
        const done = await api.post<Check>(`/learning-requests/${req.id}/diagnostic/answer`, { answers: picked });
        setReq(await api.get<LearningRequest>(`/learning-requests/${req.id}`));
        return done;
      },
      setCheck,
    );
  };
  const share = () => {
    if (req) run(() => api.post<LearningRequest>(`/learning-requests/${req.id}/share`, { consent, credit }), setReq);
  };
  const unshare = () => {
    if (req) run(() => api.post<LearningRequest>(`/learning-requests/${req.id}/unshare`, {}), setReq);
  };
  const resume = (id: string) =>
    run(() => api.post('/enrollments/switch', { enrollment: id }), () => router.push('/today'));

  if (unavailable) {
    return (
      <Page narrow>
        <PageHeader title={t('today.build.title')} description={t('new.unavailable')} />
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
        eyebrow={t('new.eyebrow')}
        title={t('new.title')}
        description={t('new.description')}
      />

      {!req && mine.length > 1 ? (
        <section className="mb-8" aria-label="Your courses">
          <h2 className="mb-2 font-semibold">{t('new.mine')}</h2>
          <ul className="space-y-2">
            {mine.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3 rounded-xl border bg-card px-4 py-3">
                <span>{e.title}</span>
                {e.active ? (
                  <span className="text-sm text-muted-foreground">{t('new.current')}</span>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => resume(e.id)} disabled={busy}>
                    {t('new.resume')}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {!req ? (
        <div className="space-y-8">
          <div>
            <label htmlFor="subject" className="mb-2 block font-semibold">
              {t('new.subject')}
            </label>
            <Input
              id="subject"
              value={text}
              maxLength={500}
              onChange={(e) => setText(e.target.value)}
              placeholder={t('new.placeholder')}
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
              <legend className="mb-2 font-semibold">{tx(`new.group.${group.id}`, GROUP_TITLE[group.id] ?? group.id)}</legend>
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
            {busy ? t('new.making') : t('new.make')}
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
                {req.ready} of {req.total} lessons are ready. The first lessons are written as soon as you start, the
                rest just before you reach them, and nothing is shown as ready until it is. Courses made by AI are
                labelled as such.
              </p>
              {changes.length ? (
                <div className="mt-4 rounded-xl border px-4 py-3 text-sm">
                  <p className="font-medium">Changes to your plan</p>
                  <ul className="mt-1 grid gap-1 text-muted-foreground">
                    {changes.map(c => <li key={c.version}>{c.change} Why: {c.reason}</li>)}
                  </ul>
                </div>
              ) : null}
              {req.published && writing ? (
                <Button className="mt-3" variant="outline" size="sm" onClick={stopWriting} disabled={busy}>
                  Stop lessons that have not started
                </Button>
              ) : null}
              {req.blueprint.assumptions?.length || req.blueprint.unresolved?.length ? (
                <div className="mt-4 rounded-xl border px-4 py-3 text-sm">
                  <p className="font-medium">What the plan assumes</p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-5 text-muted-foreground">
                    {(req.blueprint.assumptions ?? []).map((a) => <li key={a}>{a}</li>)}
                    {(req.blueprint.unresolved ?? []).map((u) => <li key={u}>Not settled yet: {u}</li>)}
                  </ul>
                </div>
              ) : null}
              {req.blueprint.modules.map((m) => (
                <div key={m.id} className="mt-5">
                  <h3 className="font-semibold">{m.title}</h3>
                  <ol className="mt-2 space-y-2">
                    {m.concepts.map((c) => (
                      <li key={c.id} className="rounded-xl border bg-card px-4 py-3">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <p className="font-medium">{c.title}</p>
                          {req.published && c.generation ? (
                            <span className="text-[13px] text-muted-foreground">{STAGE[c.generation] ?? c.generation}</span>
                          ) : null}
                        </div>
                        {c.objectives.length ? (
                          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted-foreground">
                            {c.objectives.map((o) => <li key={o}>{o}</li>)}
                          </ul>
                        ) : null}
                        {c.evidence?.length || c.minutes ? (
                          <p className="mt-1 text-[13px] text-muted-foreground">
                            {c.minutes ? `About ${c.minutes} min.` : null}
                            {c.evidence?.length ? ` You will ${c.evidence.map((e) => EVIDENCE[e] ?? e).join(', ')}.` : null}
                          </p>
                        ) : null}
                        {c.prerequisites.length ? (
                          <p className="text-[13px] text-muted-foreground">After: {c.prerequisites.join(', ')}</p>
                        ) : null}
                        {req.published && RETRYABLE.has(c.generation ?? '') ? (
                          <Button className="mt-2" variant="outline" size="sm" onClick={() => regenerate(c.id)} disabled={busy}>
                            Try writing it again
                          </Button>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </section>
          ) : null}

          {req.blueprint && !req.published ? (
            <section className="rounded-[20px] border bg-card p-5" aria-label="Where to start">
              <h2 className="font-semibold">Where should you start?</h2>
              {!check ? (
                <>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Answer a few questions so Socrat can pick a starting point. It does not count as mastery, and you
                    can skip it and start from the beginning.
                  </p>
                  <Button className="mt-3" variant="outline" onClick={startCheck} disabled={busy}>
                    {req.diagnostic === 'none' ? 'Check where to start' : 'Open my check'}
                  </Button>
                </>
              ) : check.done && check.result ? (
                <div className="mt-2 text-sm">
                  <p>
                    You got {check.result.correct} of {check.result.total}. Suggested start: {check.result.level_label}.
                  </p>
                  <ul className="mt-2 space-y-1">
                    {check.result.review.map((r) => (
                      <li key={r.concept}>
                        {r.correct ? 'Got it' : 'To learn'}: {r.concept.replace(/-/g, ' ')}
                        {r.correct ? '' : `. ${r.why}`}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="mt-3 space-y-5">
                  {check.questions.map((q, qi) => (
                    <fieldset key={q.concept}>
                      <legend className="font-medium">
                        {qi + 1}. {q.stem}
                      </legend>
                      <div className="mt-2 flex flex-col gap-2">
                        {q.options.map((o, oi) => (
                          <label key={o} className="flex items-start gap-2 text-sm">
                            <input
                              type="radio"
                              name={`q${qi}`}
                              checked={picked[qi] === oi}
                              onChange={() => setPicked((p) => p.map((v, i) => (i === qi ? oi : v)))}
                            />
                            {o}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  ))}
                  <p className="text-[13px] text-muted-foreground">{check.note}</p>
                  <Button onClick={submitCheck} disabled={busy}>
                    See my starting point
                  </Button>
                </div>
              )}
            </section>
          ) : null}

          {req.published && req.community ? (
            <section className="rounded-[20px] border bg-card p-5" aria-label="Share with the community">
              <h2 className="font-semibold">Share this course</h2>
              {req.community.shared ? (
                <>
                  <p className="mt-2 text-sm">
                    Shared{req.community.credit ? ` as ${req.community.credit}` : ' anonymously'}.{' '}
                    {req.community.learners} other learner{req.community.learners === 1 ? '' : 's'} active so far.
                  </p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {req.community.tiers.map((t) => (
                      <li key={t.id}>
                        {t.earned ? 'Earned' : `At ${t.learners} learners`}: {t.label}
                      </li>
                    ))}
                  </ul>
                  <Button variant="outline" className="mt-3" onClick={unshare} disabled={busy}>
                    Stop sharing
                  </Button>
                  <p className="mt-2 text-[13px] text-muted-foreground">
                    Learners who already started keep their progress. Rewards you earned stay yours.
                  </p>
                </>
              ) : (
                <>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Let other learners take this course. When enough of them really use it you earn rewards:{' '}
                    {req.community.tiers.map((t) => `${t.label} at ${t.learners} learners`).join(', ')}.
                  </p>
                  <label className="mt-3 flex items-start gap-2 text-sm">
                    <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1" />
                    I agree to share this course with all Socrat learners. I can stop sharing at any time.
                  </label>
                  <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="How to be credited">
                    <Pill pressed={credit === 'anonymous'} onClick={() => setCredit('anonymous')}>Anonymous</Pill>
                    <Pill pressed={credit === 'name'} onClick={() => setCredit('name')}>Show my name</Pill>
                  </div>
                  <Button className="mt-3" onClick={share} disabled={busy || !consent}>
                    Share with everyone
                  </Button>
                </>
              )}
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
