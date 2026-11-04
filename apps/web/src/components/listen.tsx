'use client';

import { useEffect, useRef, useState } from 'react';
import { Headphones, Pause, Play, Square } from 'lucide-react';
import { canSpeak, lessonText, speakableChunks } from '@/lib/speech';
import { Button } from '@/components/ui/button';

type State = 'idle' | 'playing' | 'paused';

/**
 * Listen to the lesson instead of reading it, with the browser's own voice. Nothing is sent
 * anywhere. Hidden where the browser has no speech synthesis, so it never shows a dead button.
 */
export function Listen({ target, lang }: { target: string; lang?: string }) {
  const [supported, setSupported] = useState(false);
  const [state, setState] = useState<State>('idle');
  const queue = useRef<string[]>([]);
  const stopped = useRef(false);

  useEffect(() => {
    setSupported(canSpeak());
    return () => { if (canSpeak()) window.speechSynthesis.cancel(); };
  }, []);

  function speakNext() {
    const next = queue.current.shift();
    if (!next || stopped.current) { setState('idle'); return; }
    const utterance = new SpeechSynthesisUtterance(next);
    utterance.lang = lang || document.documentElement.lang || 'en';
    utterance.rate = 1;
    utterance.onend = () => speakNext();
    utterance.onerror = () => setState('idle');
    window.speechSynthesis.speak(utterance);
  }

  function start() {
    const root = document.querySelector<HTMLElement>(target);
    if (!root) return;
    window.speechSynthesis.cancel();
    stopped.current = false;
    queue.current = speakableChunks(lessonText(root));
    if (!queue.current.length) return;
    setState('playing');
    speakNext();
  }

  function stop() {
    stopped.current = true;
    queue.current = [];
    window.speechSynthesis.cancel();
    setState('idle');
  }

  if (!supported) return null;
  return (
    <div className="mb-6 flex flex-wrap items-center gap-2" role="group" aria-label="Listen to this lesson">
      {state === 'idle' ? (
        <Button type="button" variant="outline" size="sm" onClick={start}>
          <Headphones data-icon="inline-start" /> Listen to the lesson
        </Button>
      ) : (
        <>
          {state === 'playing' ? (
            <Button type="button" variant="outline" size="sm" onClick={() => { window.speechSynthesis.pause(); setState('paused'); }}>
              <Pause data-icon="inline-start" /> Pause
            </Button>
          ) : (
            <Button type="button" variant="outline" size="sm" onClick={() => { window.speechSynthesis.resume(); setState('playing'); }}>
              <Play data-icon="inline-start" /> Resume
            </Button>
          )}
          <Button type="button" variant="ghost" size="sm" onClick={stop}>
            <Square data-icon="inline-start" /> Stop
          </Button>
          <span className="text-[13px] text-muted-foreground" aria-live="polite">{state === 'playing' ? 'Reading aloud' : 'Paused'}</span>
        </>
      )}
    </div>
  );
}
