'use client';

import { useState } from 'react';
import { Play } from 'lucide-react';
import { Difficulty, Page, Ring, StatCard } from '@/components/common';
import { Choice, Pill } from '@/components/choice';
import { ArrowButton } from '@/components/socrat/arrow-button';
import { CopyCodeBlock } from '@/components/socrat/copy-code-block';
import { Illustration, Soc, type IllustrationName } from '@/components/socrat/illustration';
import { NodeMap } from '@/components/socrat/node-map';
import { EmptyState, ErrorState, LockedState, SuccessLine } from '@/components/socrat/states';
import { STATUS_LABEL, StatusIcon, StatusLabel, StatusLegend, type Status } from '@/components/socrat/status';
import { WeekStrip } from '@/components/socrat/week-strip';
import { Mark, Wordmark } from '@/components/socrat/wordmark';
import { SocFigure, type SocMood } from '@/components/socrat/soc';
import { VisualizationHost } from '@/components/visualization-host';
import { Badge } from '@/components/ui/badge';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

const STATUSES = Object.keys(STATUS_LABEL) as Status[];
const MOODS: SocMood[] = ['neutral', 'worried', 'curious', 'thinking', 'happy', 'proud', 'surprised', 'confused', 'sleepy', 'wink'];
const ILLUSTRATIONS: IllustrationName[] = ['welcome', 'orbit', 'stack', 'ladder', 'empty', 'bulb', 'target', 'plane'];

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4 border-t py-8">
      <h2 className="font-display text-2xl font-semibold tracking-[-0.03em]">{title}</h2>
      {children}
    </section>
  );
}

export default function Gallery() {
  const [pressed, setPressed] = useState(false);
  const [choice, setChoice] = useState(1);
  return (
    <Page wide>
      <h1 className="type-display-l">Component gallery</h1>
      <p className="mt-3 text-muted-foreground">Development only. Switch the theme from the account menu or your system setting to review dark and light.</p>

      <Block title="Type">
        <p className="type-display-xl">Learn it.</p>
        <p className="type-display-l">Display L</p>
        <p className="type-display-m">Display M, 3 skills</p>
        <p className="type-title">Title</p>
        <p className="type-body-l max-w-[68ch]">Body L for reading. A lesson column stays under 68 characters per line.</p>
        <p>Body 16 px, weight 500.</p>
        <p className="text-sm text-muted-foreground">Small, muted metadata.</p>
        <p className="type-label">Label</p>
      </Block>

      <Block title="Brand">
        <div className="flex flex-wrap items-center gap-6"><Wordmark /><Mark size={48} /><Soc size={56} label="Ask Soc, your tutor" /></div>
      </Block>

      <Block title="Soc">
        <div className="flex flex-wrap items-end gap-8">
          <SocFigure books mood="worried" size={260} idle />
          <div className="flex items-end gap-4"><Soc size={96} mood="happy" /><Soc size={48} /><Soc size={32} mood="thinking" /></div>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          {MOODS.map(mood => <figure key={mood} className="paper grid justify-items-center gap-2 rounded-card p-4"><SocFigure mood={mood} size={150} /><figcaption className="text-sm">{mood}</figcaption></figure>)}
        </div>
      </Block>

      <Block title="Status system">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STATUSES.map(s => <StatusLabel key={s} status={s} size={28} />)}
        </div>
        <StatusLegend />
        <div className="flex gap-4">{STATUSES.map(s => <StatusIcon key={s} status={s} size={32} title={STATUS_LABEL[s]} />)}</div>
      </Block>

      <Block title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Start session<ArrowCircle /></Button>
          <Button variant="outline">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Log in</Button>
          <Button variant="run"><Play /> Run tests</Button>
          <Button>Submit solution<ArrowCircle /></Button>
          <Button variant="destructive">Delete account</Button>
          <Button variant="attention">Delete permanently</Button>
          <Button disabled>Disabled</Button>
          <Button aria-busy>Saving<ArrowCircle loading /></Button>
          <ArrowButton href="#" label="Open" onColor={false} />
        </div>
        <Card tone="hero"><div className="flex flex-wrap items-center gap-3 px-(--card-spacing)"><Button variant="ink">Start session<ArrowCircle /></Button><ArrowButton href="#" label="Open" /><Badge>practice</Badge><Badge>45 min</Badge><StatusIcon status="practised" size={28} /></div></Card>
      </Block>

      <Block title="Cards">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(['hero', 'lilac', 'cream', 'surface', 'raised', 'outlined'] as const).map(tone => (
            <Card key={tone} tone={tone}><div className="px-(--card-spacing)"><p className="type-label">{tone}</p><p className="mt-2 font-display text-2xl font-bold">Card title</p><p className="mt-1 text-sm">Supporting line.</p></div></Card>
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-3"><StatCard value={3} label="Skills mastered" icon={<StatusIcon status="mastered" size={28} />} hint="One-line definition." /><StatCard value={1} label="Review due" icon={<StatusIcon status="review" size={28} />} /><StatCard value={2} label="Need practice" icon={<StatusIcon status="needs_practice" size={28} />} /></div>
      </Block>

      <Block title="Inputs and controls">
        <div className="grid max-w-md gap-2"><label htmlFor="g-input" className="font-semibold">Label</label><Input id="g-input" aria-describedby="g-help" /><p id="g-help" className="text-sm text-muted-foreground">Helper text below.</p></div>
        <div className="flex flex-wrap gap-2"><Pill pressed={pressed} onClick={() => setPressed(p => !p)}>45 min</Pill><Pill pressed={!pressed} onClick={() => setPressed(p => !p)}>Mon</Pill></div>
        <label className="flex items-center gap-3"><Switch /> Reduce motion</label>
        <Tabs defaultValue="a"><TabsList><TabsTrigger value="a">Problems</TabsTrigger><TabsTrigger value="b">Company questions</TabsTrigger><TabsTrigger value="c">Focus sprint</TabsTrigger></TabsList></Tabs>
        <div className="grid max-w-xl gap-3" role="radiogroup" aria-label="Sample answers">
          {['Unanswered', 'Selected'].map((label, i) => <Choice key={label} role="radio" aria-checked={choice === i} selected={choice === i} note={choice === i ? 'Selected' : undefined} marker={String.fromCharCode(65 + i)} onClick={() => setChoice(i)}>{label}</Choice>)}
          <Choice role="radio" aria-checked tone="correct" note="Correct" marker="C" disabled>Checked correct</Choice>
          <Choice role="radio" aria-checked={false} tone="wrong" note="Incorrect" marker="D" disabled>Checked incorrect</Choice>
        </div>
      </Block>

      <Block title="Progress">
        <div className="flex flex-wrap items-center gap-6"><Ring value={72} size={80} label="72%" /><div className="w-64"><Progress value={72} aria-label="Sample progress" /></div><Difficulty level="easy" /><Difficulty level="medium" /><Difficulty level="hard" /></div>
        <div className="max-w-md"><WeekStrip studiedToday /></div>
      </Block>

      <Block title="Skill map">
        <Card><div className="px-(--card-spacing)"><NodeMap label="Sample" nodes={STATUSES.map((s, i) => ({ id: s, title: STATUS_LABEL[s], href: '#', status: s, current: i === 3 }))} /></div></Card>
      </Block>

      <Block title="States">
        <EmptyState title="No problems match" action={<Button variant="outline">Clear filters</Button>}>Remove a filter or search for a different skill.</EmptyState>
        <ErrorState message="Could not reach Socrat. Check your connection and try again." retry={() => undefined} />
        <LockedState title="Locked until First steps" href="#">Pass the checkpoint to unlock practice and checks.</LockedState>
        <SuccessLine>Saved.</SuccessLine>
        <div className="grid gap-2"><Skeleton className="h-6 w-64" /><Skeleton className="h-24 w-full rounded-card" /></div>
      </Block>

      <Block title="Code">
        <CopyCodeBlock lang="python" code={'def find_pair(numbers, target):\n    left, right = 0, len(numbers) - 1'} />
      </Block>

      <Block title="Lesson visuals">
        <div className="grid gap-6" data-testid="lesson-visuals">
          <VisualizationHost spec={{ renderer: 'simulation', version: '1.0', params: { model: 'circuit', inputs: { voltage: 10, resistance: 5 } }, purpose: 'See current change with resistance', fallback_text: 'Ohm law: current is voltage divided by resistance, so 10 V across 5 ohm gives 2 A.', alt_text: 'A circuit with one resistor.' }} />
          <VisualizationHost spec={{ renderer: 'timeline', version: '1.0', params: { unit: 'beat', length: 8, tracks: ['Kick', 'Snare'] }, purpose: 'Place beats on a bar', fallback_text: 'Eight beats: kick on 1 and 5, snare on 3 and 7.', alt_text: 'Two tracks of eight beats.' }} />
          <VisualizationHost spec={{ renderer: 'code-studio', version: '1.0', params: { language: 'python', starter: 'def solve(x):\n    return x' }, purpose: 'Try a starter', fallback_text: 'Write solve(x) so it returns x doubled.', alt_text: 'A Python starter function.' }} />
        </div>
      </Block>

      <Block title="Illustrations">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">{ILLUSTRATIONS.map(name => <figure key={name} className="grid gap-2 rounded-card border p-4"><Illustration name={name} draw="load" /><figcaption className="text-center text-sm">{name}</figcaption></figure>)}</div>
      </Block>
    </Page>
  );
}
