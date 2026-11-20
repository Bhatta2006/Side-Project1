'use client';
// Socrat's own sounds, synthesised in the browser (no audio files, nothing borrowed).
// The motif is stone and wood, after the pebble family:
//   tap      a small pebble clack (filtered click)
//   correct  a warm marimba rising fourth, D5 then G5, with a pebble tick on top
//   wrong    a low soft wooden knock, two notes falling a tone; never a buzzer
//   combo    the correct sound, one step higher for each answer in a run (capped)
//   finish   pebbles skipping across water: quick clacks speeding up, then a resolved chord
//   streak   a rising pentatonic roll on the marimba
// Plus a short vibration on phones that support it. Both follow the learner's sound setting.

const SOUND_KEY = 'socrat:sound';

export function soundOn(): boolean {
  try { return localStorage.getItem(SOUND_KEY) !== 'off'; } catch { return true; }
}
export function setSoundOn(on: boolean) {
  try { localStorage.setItem(SOUND_KEY, on ? 'on' : 'off'); } catch { /* blocked: this visit only */ }
}

let ctx: AudioContext | null = null;
function audio(): AudioContext | null {
  if (typeof window === 'undefined' || !soundOn()) return null;
  const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AC) return null;
  ctx ??= new AC();
  if (ctx.state === 'suspended') void ctx.resume();
  return ctx;
}

const hz = (midi: number) => 440 * 2 ** ((midi - 69) / 12);

/** A marimba-like bar: a sine with its 4th harmonic, a quick strike and a woody decay. */
function bar(a: AudioContext, midi: number, at: number, gain = 0.22, decay = 0.55) {
  const out = a.createGain();
  out.gain.setValueAtTime(0.0001, at);
  out.gain.exponentialRampToValueAtTime(gain, at + 0.006);
  out.gain.exponentialRampToValueAtTime(0.0001, at + decay);
  out.connect(a.destination);
  for (const [mult, level] of [[1, 1], [4, 0.18], [10, 0.04]] as const) {
    const o = a.createOscillator();
    const g = a.createGain();
    o.type = 'sine';
    o.frequency.value = hz(midi) * mult;
    g.gain.value = level;
    // Overtones die faster than the fundamental, as on a real bar.
    if (mult > 1) { g.gain.setValueAtTime(level, at); g.gain.exponentialRampToValueAtTime(0.0001, at + decay / (mult / 2)); }
    o.connect(g).connect(out);
    o.start(at);
    o.stop(at + decay + 0.05);
  }
}

/** A pebble clack: a very short noise burst through a bright band-pass filter. */
function clack(a: AudioContext, at: number, pitch = 2600, gain = 0.25) {
  const len = Math.floor(a.sampleRate * 0.03);
  const buf = a.createBuffer(1, len, a.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len) ** 3;
  const src = a.createBufferSource();
  src.buffer = buf;
  const bp = a.createBiquadFilter();
  bp.type = 'bandpass';
  bp.frequency.value = pitch;
  bp.Q.value = 6;
  const g = a.createGain();
  g.gain.value = gain;
  src.connect(bp).connect(g).connect(a.destination);
  src.start(at);
}

/** A soft wooden knock: a low sine that drops in pitch quickly. */
function knock(a: AudioContext, midi: number, at: number, gain = 0.28) {
  const o = a.createOscillator();
  const g = a.createGain();
  o.type = 'sine';
  o.frequency.setValueAtTime(hz(midi) * 1.5, at);
  o.frequency.exponentialRampToValueAtTime(hz(midi), at + 0.05);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(gain, at + 0.008);
  g.gain.exponentialRampToValueAtTime(0.0001, at + 0.28);
  o.connect(g).connect(a.destination);
  o.start(at);
  o.stop(at + 0.32);
}

function buzz(pattern: number | number[]) {
  try { if (soundOn()) navigator.vibrate?.(pattern); } catch { /* not supported */ }
}

export type GameSound = 'tap' | 'correct' | 'wrong' | 'finish' | 'streak';

/** Plays one of Socrat's sounds. `run` raises the correct sound by a step per answer in a row. */
export function play(sound: GameSound, run = 0) {
  const a = audio();
  if (sound === 'correct') buzz(18);
  if (sound === 'wrong') buzz([30, 40, 30]);
  if (!a) return;
  const t = a.currentTime + 0.01;
  // D major pentatonic steps for the combo climb: D, E, F#, A, B.
  const lift = [0, 2, 4, 7, 9][Math.min(Math.max(run - 1, 0), 4)];
  switch (sound) {
    case 'tap':
      clack(a, t, 3200, 0.12);
      break;
    case 'correct':
      bar(a, 74 + lift, t, 0.2, 0.45);
      bar(a, 79 + lift, t + 0.09, 0.24, 0.7);
      clack(a, t + 0.09, 4200, 0.08);
      break;
    case 'wrong':
      knock(a, 50, t);
      knock(a, 48, t + 0.13, 0.22);
      break;
    case 'finish': {
      // Skipping pebbles: the gaps shrink, the clacks get lighter, then the chord.
      let at = t;
      [0.16, 0.13, 0.1, 0.08, 0.065].forEach((gap, i) => { clack(a, at, 2200 + i * 350, 0.22 - i * 0.03); at += gap; });
      [62, 66, 69, 74].forEach((m, i) => bar(a, m, at + 0.05 + i * 0.03, 0.17, 1.4));
      break;
    }
    case 'streak':
      [62, 64, 66, 69, 71, 74].forEach((m, i) => bar(a, m, t + i * 0.06, 0.16, 0.6));
      break;
  }
}
