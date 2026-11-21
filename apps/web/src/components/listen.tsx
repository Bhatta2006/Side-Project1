'use client';

import { useEffect, useRef, useState } from 'react';
import { Headphones, Pause, Play, Square } from '@/components/icons';
import { canSpeak, lessonText, speakableChunks } from '@/lib/speech';
import { Button } from '@/components/ui/button';

type State = 'idle' | 'loading' | 'playing' | 'paused';

/**
 * Listen to the lesson instead of reading it. With `remote` (the API's speech URL for this
 * lesson, learn/speech.py) each page is read by a natural Gemini voice, page after page, the
 * next one fetched while this one plays. Without it, or when the first page cannot be fetched,
 * the browser's own voice reads the text on screen: nothing is sent anywhere. Hidden when
 * neither is available, so it never shows a dead button.
 */
export function Listen({ target, lang, remote }: { target: string; lang?: string; remote?: string }) {
  const [supported, setSupported] = useState(false);
  const [state, setState] = useState<State>('idle');
  const queue = useRef<string[]>([]);
  const stopped = useRef(false);
  const audio = useRef<HTMLAudioElement | null>(null);
  const ahead = useRef<HTMLAudioElement | null>(null);
  const [mode, setMode] = useState<'remote' | 'browser'>(remote ? 'remote' : 'browser');

  useEffect(() => {
    setSupported(Boolean(remote) || canSpeak());
    return () => {
      if (canSpeak()) window.speechSynthesis.cancel();
      audio.current?.pause();
    };
  }, [remote]);

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

  function startBrowser() {
    const root = document.querySelector<HTMLElement>(target);
    if (!root || !canSpeak()) { setState('idle'); return; }
    window.speechSynthesis.cancel();
    setMode('browser');
    queue.current = speakableChunks(lessonText(root));
    if (!queue.current.length) { setState('idle'); return; }
    setState('playing');
    speakNext();
  }

  function playPage(page: number) {
    if (stopped.current || !remote) return;
    const url = `${remote}?page=${page}`;
    const el = ahead.current?.src.endsWith(url) ? ahead.current : new Audio(url);
    audio.current = el;
    el.onplaying = () => {
      setState('playing');
      ahead.current = new Audio(`${remote}?page=${page + 1}`); // fetched while this page plays
      ahead.current.preload = 'auto';
    };
    el.onended = () => playPage(page + 1);
    // Past the last page the API answers 404 and the reading ends; a failure on the first
    // page means no Gemini voice now, so the browser reads instead.
    el.onerror = () => (page === 0 ? startBrowser() : setState('idle'));
    void el.play().catch(() => (page === 0 ? startBrowser() : setState('idle')));
  }

  function start() {
    stopped.current = false;
    if (remote) {
      setMode('remote');
      setState('loading');
      playPage(0);
    } else startBrowser();
  }

  function stop() {
    stopped.current = true;
    queue.current = [];
    if (canSpeak()) window.speechSynthesis.cancel();
    audio.current?.pause();
    audio.current = ahead.current = null;
    setState('idle');
  }

  function pause() {
    if (mode === 'remote') audio.current?.pause();
    else window.speechSynthesis.pause();
    setState('paused');
  }

  function resume() {
    if (mode === 'remote') void audio.current?.play();
    else window.speechSynthesis.resume();
    setState('playing');
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
          {state === 'paused' ? (
            <Button type="button" variant="outline" size="sm" onClick={resume}>
              <Play data-icon="inline-start" /> Resume
            </Button>
          ) : (
            <Button type="button" variant="outline" size="sm" onClick={pause} disabled={state === 'loading'}>
              <Pause data-icon="inline-start" /> Pause
            </Button>
          )}
          <Button type="button" variant="ghost" size="sm" onClick={stop}>
            <Square data-icon="inline-start" /> Stop
          </Button>
          <span className="text-[13px] text-muted-foreground" aria-live="polite">
            {state === 'loading' ? 'Preparing the voice…' : state === 'playing' ? 'Reading aloud' : 'Paused'}
          </span>
        </>
      )}
    </div>
  );
}
