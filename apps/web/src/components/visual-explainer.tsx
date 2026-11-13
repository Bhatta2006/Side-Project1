'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { ChevronLeft, ChevronRight, Expand, Info, Pause, Play, RotateCcw, Star, X } from '@/components/icons';
import type { VisualArtifact, VisualState } from '@/lib/explainer';
import { useReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { AttentionIcon } from '@/components/socrat/states';
import './visual-explainer.css';

type Failure = '' | 'load' | 'stopped';

/**
 * The generated visual and its host controls, read as one object: the canvas fills the card
 * and the control dock is attached inside its bottom edge. The frame stays opaque-origin and
 * network-blocked; only step, reset and theme messages cross the boundary.
 */
export default function VisualExplainer({ artifact, onExplain, onReport, onBack }: {
  artifact: VisualArtifact;
  onExplain?: () => void;
  onReport?: () => void;
  onBack?: () => void;
}) {
  const { resolvedTheme } = useTheme();
  const [nonce, setNonce] = useState(0);
  const frameSource = useMemo(() => {
    const url = new URL(artifact.frame_url);
    url.searchParams.set('theme', resolvedTheme === 'dark' ? 'dark' : 'light');
    return url.toString();
    // `nonce` reloads the same visual after a preview failure.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact.frame_url, resolvedTheme, nonce]);
  const frame = useRef<HTMLIFrameElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const heartbeat = useRef(Date.now());
  const everReady = useRef(false);
  const themeAtLoad = useRef(resolvedTheme);
  const latest = useRef<VisualState>({ count: artifact.qa.step_count, current: 0, description: '', height: 650 });
  const [state, setState] = useState(latest.current);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<Failure>('');
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState('1');
  const motion = useReducedMotion();
  const [reduced, setReduced] = useState(false);
  const [full, setFull] = useState<'' | 'native' | 'overlay'>('');
  const [themeNote, setThemeNote] = useState(false);
  const [portrait, setPortrait] = useState(false);

  // The app's reduce-motion setting (or the system's) turns playback off; the switch can too.
  useEffect(() => { setReduced(motion.reduced); if (motion.reduced) setPlaying(false); }, [motion.reduced]);

  const send = useCallback((data: Record<string, unknown>) => {
    frame.current?.contentWindow?.postMessage({ ...data, channel: artifact.id }, '*');
  }, [artifact.id]);
  const theme = useCallback(() => {
    const styles = getComputedStyle(document.documentElement);
    const names = ['background', 'foreground', 'card', 'muted', 'muted-foreground', 'border', 'primary', 'primary-foreground', 'success', 'warning', 'destructive', 'chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5', 'radius'];
    const tokens = Object.fromEntries(names.map(name => [name, styles.getPropertyValue('--' + name).trim()]));
    // The document sits on the card surface, so there is no seam between canvas and card.
    tokens.background = styles.getPropertyValue('--card').trim();
    send({ type: 'theme', tokens, dark: resolvedTheme === 'dark', reducedMotion: reduced });
  }, [send, resolvedTheme, reduced]);

  useEffect(() => {
    function message(event: MessageEvent) {
      if (event.origin !== 'null' || event.source !== frame.current?.contentWindow || event.data?.channel !== artifact.id) return;
      const data = event.data;
      if (data.type === 'ready') { heartbeat.current = Date.now(); everReady.current = true; setReady(true); }
      else if (data.type === 'heartbeat') heartbeat.current = Date.now();
      else if (data.type === 'error') { setFailure('stopped'); setPlaying(false); }
      else if (data.type === 'state' && Number.isInteger(data.count) && data.count >= 1 && data.count <= 2000 && Number.isInteger(data.current) && data.current >= 0 && data.current < data.count && typeof data.description === 'string' && data.description.length <= 6000 && Number.isFinite(data.height)) {
        everReady.current = true;
        setReady(true);
        const next = { count: data.count, current: data.current, description: data.description, height: Math.min(1600, Math.max(420, data.height)), timed: data.timed === true, playing: data.playing === true };
        latest.current = next;
        setState(previous => previous.count === next.count && previous.current === next.current && previous.description === next.description && previous.height === next.height && previous.timed === next.timed && previous.playing === next.playing ? previous : next);
      }
    }
    addEventListener('message', message);
    const watchdog = setInterval(() => {
      if (document.hidden) { heartbeat.current = Date.now(); return; }
      // A first load crosses to the sandbox domain and can be slow on phones; a running visual
      // that stops beating has stalled.
      if (Date.now() - heartbeat.current > (everReady.current ? 8000 : 20000)) { setFailure(everReady.current ? 'stopped' : 'load'); setPlaying(false); }
    }, 1000);
    return () => { removeEventListener('message', message); clearInterval(watchdog); };
  }, [artifact.id]);
  useEffect(() => { if (ready) theme(); }, [ready, theme]);
  useEffect(() => {
    setReady(false); setPlaying(false); heartbeat.current = Date.now(); everReady.current = false;
    if (themeAtLoad.current !== resolvedTheme) { setThemeNote(true); themeAtLoad.current = resolvedTheme; }
  }, [frameSource, resolvedTheme]);
  useEffect(() => {
    if (!playing || reduced || !ready || failure || latest.current.timed) return;
    const timer = setInterval(() => {
      const current = latest.current;
      if (current.current >= current.count - 1) { setPlaying(false); return; }
      send({ type: 'step', index: current.current + 1 });
    }, 1400 / Number(speed));
    return () => clearInterval(timer);
  }, [playing, reduced, ready, failure, send, speed]);

  // Expanded view: the Fullscreen API where available, otherwise a fixed overlay with a focus trap.
  useEffect(() => {
    const update = () => setFull(document.fullscreenElement === canvas.current ? 'native' : f => (f === 'native' ? '' : f));
    document.addEventListener('fullscreenchange', update);
    return () => document.removeEventListener('fullscreenchange', update);
  }, []);
  useEffect(() => {
    if (!full) return;
    closeButton.current?.focus();
    const query = window.matchMedia('(orientation: portrait) and (max-width: 767px)');
    setPortrait(query.matches);
    if (full !== 'overlay') return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setFull(''); return; }
      if (event.key !== 'Tab' || !canvas.current) return;
      const items = [...canvas.current.querySelectorAll<HTMLElement>('button:not(:disabled), select, input, iframe, [tabindex="0"]')];
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [full]);
  async function expand() {
    if (full === 'native') { await document.exitFullscreen().catch(() => undefined); return; }
    if (full === 'overlay') { setFull(''); return; }
    try {
      if (!canvas.current?.requestFullscreen) throw new Error('unsupported');
      await canvas.current.requestFullscreen();
    } catch {
      setFull('overlay');
    }
  }

  // A film keeps playing across a chapter jump; a stepped visual pauses.
  function seek(index: number) { if (!state.timed) setPlaying(false); send({ type: 'step', index }); }
  const isPlaying = state.timed ? Boolean(state.playing) : playing;
  function togglePlay() {
    if (state.timed) { send({ type: isPlaying ? 'pause' : 'play' }); return; }
    if (state.current === state.count - 1) seek(0);
    setPlaying(value => !value);
  }
  function changeSpeed(value: string) { setSpeed(value); if (state.timed) send({ type: 'rate', value: Number(value) }); }
  function reload() { setFailure(''); setNonce(n => n + 1); }
  const steps = state.count > 1;
  const disabled = !ready || Boolean(failure);
  const stepLabel = steps ? `${state.timed ? 'Chapter' : 'Step'} ${state.current + 1} of ${state.count}` : 'Live experiment';

  return (
    <div className="grid gap-3">
      <div
        ref={canvas}
        className={cn('visual-canvas relative flex flex-col overflow-hidden paper rounded-card', full === 'overlay' && 'fixed inset-0 z-[70] rounded-none border-0')}
        role={full === 'overlay' ? 'dialog' : undefined}
        aria-modal={full === 'overlay' ? true : undefined}
        aria-label={full ? `${artifact.title}, expanded` : undefined}
      >
        {full ? (
          <div className="flex items-center justify-between gap-3 border-b px-4 py-2">
            <p className="truncate font-semibold">{artifact.title}</p>
            {portrait ? <p className="text-[13px] text-muted-foreground">Rotate for more room</p> : null}
            <Button ref={closeButton} variant="outline" size="sm" onClick={expand}><X data-icon="inline-start" /> Close</Button>
          </div>
        ) : null}

        <div className="relative min-h-[max(420px,70dvh)] flex-1 lg:min-h-[560px]">
          {failure ? (
            <div role="alert" className="grid min-h-[inherit] place-items-center p-8 text-center">
              <div className="grid max-w-md justify-items-center gap-3">
                <AttentionIcon size={32} />
                <p className="font-display text-xl font-semibold tracking-[-0.02em]">{failure === 'load' ? 'The visual was generated but did not load.' : 'The visual stopped responding.'}</p>
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  <Button onClick={reload}>Reload visual</Button>
                  {onExplain ? <Button variant="outline" onClick={onExplain}>Read the explanation</Button> : null}
                  {onReport ? <Button variant="outline" onClick={onReport}>Report an issue</Button> : null}
                  {onBack ? <Button variant="ghost" onClick={onBack}>Back to saved visuals</Button> : null}
                </div>
              </div>
            </div>
          ) : (
            <>
              {!ready ? (
                <div className="absolute inset-0 z-10 grid place-content-center gap-4 p-8" role="status">
                  <Skeleton className="mx-auto h-40 w-64 max-w-full rounded-[4px]" />
                  <p className="text-center text-[15px] text-muted-foreground">{themeNote ? 'Applying theme.' : 'Loading the visual.'}</p>
                </div>
              ) : null}
              <iframe
                ref={frame}
                src={frameSource}
                title={artifact.title + ' — interactive visual'}
                sandbox="allow-scripts"
                referrerPolicy="no-referrer"
                allow="camera 'none'; microphone 'none'; geolocation 'none'; clipboard-read 'none'; clipboard-write 'none'"
                className="block w-full border-0"
                style={{ height: state.height, opacity: ready ? 1 : 0 }}
              />
            </>
          )}
        </div>

        {/* Control dock, attached inside the card. */}
        <div
          className="border-t bg-card px-4 py-3 lg:px-5"
          onKeyDown={event => {
            if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || disabled) return;
            if (event.key === 'ArrowRight') { event.preventDefault(); seek(Math.min(state.count - 1, state.current + 1)); }
            if (event.key === 'ArrowLeft') { event.preventDefault(); seek(Math.max(0, state.current - 1)); }
          }}
        >
          <div className="flex flex-wrap items-center gap-2">
            {steps ? (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="icon" disabled={disabled || state.current === 0} onClick={() => seek(state.current - 1)} aria-label="Previous visual step"><ChevronLeft /></Button>
                  </TooltipTrigger>
                  <TooltipContent>Previous step</TooltipContent>
                </Tooltip>
                <Button className="min-w-28" disabled={disabled || reduced} onClick={togglePlay}>
                  {isPlaying ? <Pause /> : <Play />}{isPlaying ? 'Pause' : 'Play'}
                </Button>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="icon" disabled={disabled || state.current >= state.count - 1} onClick={() => seek(state.current + 1)} aria-label="Next visual step"><ChevronRight /></Button>
                  </TooltipTrigger>
                  <TooltipContent>Next step</TooltipContent>
                </Tooltip>
              </>
            ) : <span className="type-label px-1 text-muted-foreground">Live experiment</span>}
            <Button variant="ghost" disabled={disabled} onClick={() => { setPlaying(false); send({ type: 'reset' }); }}><RotateCcw />Reset</Button>
            {steps ? <span className="px-1 text-sm font-semibold tabular-nums">{stepLabel}</span> : null}
            <div className="ml-auto flex flex-wrap items-center gap-2">
              {steps ? (
                <>
                  <label className="sr-only" htmlFor={`speed-${artifact.id}`}>Playback speed</label>
                  <NativeSelect id={`speed-${artifact.id}`} size="sm" value={speed} onChange={event => changeSpeed(event.target.value)} className="w-24">
                    <NativeSelectOption value="0.5">0.5×</NativeSelectOption>
                    <NativeSelectOption value="1">1×</NativeSelectOption>
                    <NativeSelectOption value="2">2×</NativeSelectOption>
                  </NativeSelect>
                  <label className="flex min-h-11 items-center gap-2 px-1 text-sm font-medium">
                    <Switch checked={reduced} onCheckedChange={value => { setReduced(value); if (value) setPlaying(false); }} />
                    Reduce motion
                  </label>
                </>
              ) : null}
              <Button variant="outline" onClick={expand} aria-label={full ? 'Exit expanded canvas' : 'Expand canvas'}><Expand />{full ? 'Exit' : 'Expand'}</Button>
            </div>
          </div>
          {steps ? (
            <div className="mt-2">
              <label htmlFor={`timeline-${artifact.id}`} className="sr-only">Visual timeline</label>
              <input id={`timeline-${artifact.id}`} type="range" min={0} max={state.count - 1} value={state.current} disabled={disabled} onChange={event => seek(Number(event.target.value))} className="visual-timeline" style={{ '--ticks': state.count - 1 } as React.CSSProperties} aria-valuetext={`${stepLabel}${state.description ? `: ${state.description.slice(0, 120)}` : ''}`} />
            </div>
          ) : null}
          {steps && reduced ? <p className="mt-1 text-sm text-muted-foreground">Playback is paused while reduced motion is on. Use Next and Previous to step.</p> : null}
          {!steps ? <p className="mt-1 text-sm text-muted-foreground">This is one scene. Change the inputs to explore. There is nothing to play.</p> : null}
          <p role="status" className="mt-2 min-h-6 text-[15px] leading-relaxed">{state.description}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <p className="text-[13px] text-muted-foreground">
          {/* The automatic review's flag is a star and nothing more: no notes, no description. */}
          {artifact.qa.ai_review === 'flagged' ? <span role="img" aria-label="Flagged by the automatic review" className="mr-1.5 inline-flex align-[-3px] text-pen"><Star className="size-4" aria-hidden="true" /></span> : null}
          Generated by AI and checked automatically. It can still be wrong. Compare it with your lesson.{themeNote ? ' Switching theme restarts the experiment.' : ''}</p>
        <div className="flex items-center gap-1">
          <Popover>
            <PopoverTrigger asChild><Button variant="ghost" size="sm"><Info data-icon="inline-start" /> About this visual</Button></PopoverTrigger>
            <PopoverContent align="end" className="text-[15px]">
              This visual runs in an isolated frame, separate from your account and learning data. Exploring it does not count as practice or mastery.
            </PopoverContent>
          </Popover>
          {onReport ? <Button variant="link" size="sm" onClick={onReport}>Report an issue</Button> : null}
        </div>
      </div>
    </div>
  );
}
