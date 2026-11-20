import { notFound } from 'next/navigation';
import { PebbleFriend, PEBBLE_FRIENDS, type PebbleKind } from '@/components/socrat/pebble-friend';
import { GameEmoji, type GameEmojiName } from '@/components/socrat/game-emoji';
import { Button } from '@/components/ui/button';
import { GameBar } from '@/components/socrat/game-bar';
import { SkillPath } from '@/components/socrat/skill-path';
import { AnswerDemo } from './demo';

export const metadata = { title: 'Daybreak parts' };

const EMOJI: GameEmojiName[] = ['flame', 'bolt', 'target', 'gem', 'star', 'check', 'cross', 'review', 'lock', 'trophy', 'clock', 'book'];

/** Development-only board of the Daybreak pebble family, game emoji and buttons; 404 in production. */
export default function DaybreakParts() {
  if (process.env.NODE_ENV === 'production') notFound();
  return (
    <main className="mx-auto grid max-w-3xl gap-10 px-5 py-10">
      <section className="grid gap-4">
        <h1 className="text-3xl">Pebble family</h1>
        <ul className="flex flex-wrap gap-6">
          {(Object.keys(PEBBLE_FRIENDS) as PebbleKind[]).map(k => (
            <li key={k} className="flex flex-col items-center gap-1 text-sm">
              <PebbleFriend kind={k} size={72} />
              <span className="font-bold">{PEBBLE_FRIENDS[k].name}</span>
              <span className="text-muted-foreground">{PEBBLE_FRIENDS[k].role}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="grid gap-4">
        <h2 className="text-2xl">Game emoji</h2>
        <ul className="flex flex-wrap gap-5">
          {EMOJI.map(n => (
            <li key={n} className="flex flex-col items-center gap-1 text-xs text-muted-foreground"><GameEmoji name={n} size={44} />{n}</li>
          ))}
        </ul>
      </section>
      <section className="grid gap-4">
        <h2 className="text-2xl">Game strip and path (sample data)</h2>
        <GameBar streak={6} fresh={false} studiedToday minutesDone={7} minutesGoal={10} learned={5} mastered={2} />
        <SkillPath
          label="HTTP basics"
          startLabel="Start lesson"
          nodes={[
            { id: 'a', title: 'What a request is', href: '#', status: 'mastered' },
            { id: 'b', title: 'Methods: GET and POST', href: '#', status: 'practised' },
            { id: 'c', title: 'Status codes', href: '#', status: 'practised', reviewDue: true },
            { id: 'd', title: 'Your first endpoint', href: '#', status: 'not_seen', current: true },
            { id: 'e', title: 'JSON bodies', href: '#', status: 'not_seen' },
            { id: 'f', title: 'Routing', href: '#', status: 'locked' },
            { id: 'g', title: 'Errors that help', href: '#', status: 'locked' },
          ]}
        />
      </section>
      <section className="grid gap-4">
        <h2 className="text-2xl">Answer feel</h2>
        <AnswerDemo />
      </section>
      <section className="flex flex-wrap items-center gap-4">
        <Button size="lg">Continue</Button>
        <Button variant="secondary" size="lg">Skip for now</Button>
        <Button variant="outline" size="lg">Build a REST API</Button>
        <Button variant="destructive">Remove</Button>
        <Button variant="ghost">Later</Button>
      </section>
    </main>
  );
}
