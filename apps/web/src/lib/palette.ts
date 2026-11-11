'use client';
// The learner's colours: a palette (app/palettes.css) and light, dark or the device's choice.
// Kept in this browser's localStorage and applied to <html> by PALETTE_BOOT_SCRIPT before the first
// paint, so a page never flashes the wrong colours. Classic in light is the default and changes nothing.
import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { PALETTE_KEY as KEY } from './palette-boot';

export type PaletteId = 'classic' | 'tide' | 'lilac' | 'meadow' | 'riso' | 'dusk';
export type ColourMode = 'light' | 'dark' | 'system';
export interface PalettePref { palette: PaletteId; mode: ColourMode }

/** For the picker: the desk, the hero sheet, the button and the highlighter, in light and in dark. */
export const PALETTES: readonly { id: PaletteId; name: string; note: string; light: [string, string, string, string]; dark: [string, string, string, string] }[] = [
  { id: 'classic', name: 'Classic', note: 'Sage desk, yellow sticky, orange marker.', light: ['#a8c8bb', '#f7e38a', '#df6b3c', '#f8dc4c'], dark: ['#1c2622', '#45432f', '#df6b3c', '#77703a'] },
  { id: 'tide', name: 'Tide', note: 'Sea glass: aqua paper, sea-green pen, mint highlighter.', light: ['#9ec3c9', '#cfe7ec', '#6cc3b5', '#b6edd8'], dark: ['#13232a', '#3d4749', '#6cc3b5', '#5b7169'] },
  { id: 'lilac', name: 'Lilac', note: 'Soft violet paper with a raspberry pen.', light: ['#c5bcd8', '#e6dcf6', '#b997ea', '#f8c6dc'], dark: ['#1e1a2a', '#45424f', '#b997ea', '#77606b'] },
  { id: 'meadow', name: 'Meadow', note: 'Spring green with a buttery highlighter.', light: ['#b7c99e', '#e6efc7', '#8fcb7b', '#fde58a'], dark: ['#1a2417', '#45493f', '#8fcb7b', '#7a7350'] },
  { id: 'riso', name: 'Riso', note: 'Print shop: blush desk, blue paper, pink and mint ink.', light: ['#efc8c0', '#cfe3ff', '#ff93a6', '#a3e6cb'], dark: ['#261b20', '#3f4652', '#ff93a6', '#53706a'] },
  { id: 'dusk', name: 'Dusk', note: 'Evening blue with a salmon marker.', light: ['#8fa3c4', '#dfe6f7', '#f2a59c', '#ffd98a'], dark: ['#151b29', '#45484f', '#f2a59c', '#7a6c4e'] },
];

const DEFAULT: PalettePref = { palette: 'classic', mode: 'light' };
const isPalette = (v: unknown): v is PaletteId => PALETTES.some(p => p.id === v);
const isMode = (v: unknown): v is ColourMode => v === 'light' || v === 'dark' || v === 'system';

export function readPalette(): PalettePref {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? 'null') as Partial<PalettePref> | null;
    return { palette: isPalette(raw?.palette) ? raw.palette : DEFAULT.palette, mode: isMode(raw?.mode) ? raw.mode : DEFAULT.mode };
  } catch {
    return DEFAULT;
  }
}

const prefersDark = () => typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches;

export function applyPalette(pref: PalettePref) {
  const el = document.documentElement;
  const dark = pref.mode === 'dark' || (pref.mode === 'system' && prefersDark());
  if (pref.palette !== 'classic' || dark) el.dataset.palette = pref.palette;
  else delete el.dataset.palette;
  if (dark) el.dataset.mode = 'dark';
  else delete el.dataset.mode;
}

/** "tide:dark", as the account stores it (users.appearance). */
export const toAppearance = (p: PalettePref) => `${p.palette}:${p.mode}`;
export function fromAppearance(value: string | null | undefined): PalettePref | null {
  const [palette, mode] = (value ?? '').split(':');
  return isPalette(palette) && isMode(mode) ? { palette, mode } : null;
}

const CHANGED = 'socrat:palette-changed';

/** Applies a choice and keeps it in this browser; every usePalette on the page hears about it. */
function keep(pref: PalettePref) {
  applyPalette(pref);
  try { localStorage.setItem(KEY, JSON.stringify(pref)); } catch { /* storage blocked: applies for this visit only */ }
  window.dispatchEvent(new CustomEvent<PalettePref>(CHANGED, { detail: pref }));
}

export function usePalette(): [PalettePref, (next: Partial<PalettePref>) => void] {
  const { profile } = useSession();
  const [pref, setPref] = useState<PalettePref>(DEFAULT);
  useEffect(() => {
    setPref(readPalette());
    const on = (e: Event) => setPref((e as CustomEvent<PalettePref>).detail);
    window.addEventListener(CHANGED, on);
    return () => window.removeEventListener(CHANGED, on);
  }, []);
  // "Match device" follows the device when it switches between light and dark.
  useEffect(() => {
    if (pref.mode !== 'system' || typeof matchMedia !== 'function') return;
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const on = () => applyPalette(pref);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [pref]);
  const set = useCallback((next: Partial<PalettePref>) => {
    const merged = { ...pref, ...next };
    keep(merged);
    // Signed in: save it on the account too, so it follows the learner to other devices.
    if (profile) api.patch('/me', { appearance: toAppearance(merged) }).catch(() => { /* kept in this browser */ });
  }, [pref, profile]);
  return [pref, set];
}

/**
 * On every page: brings the account's colours to this browser when the learner signs in, and
 * the first time a browser choice meets an account with none, saves it there. Also keeps
 * "Match device" in step (through usePalette).
 */
export function PaletteSync() {
  const { profile } = useSession();
  usePalette();
  const id = profile?.id;
  const saved = profile?.appearance;
  useEffect(() => {
    if (!id) return;
    const account = fromAppearance(saved);
    const local = readPalette();
    if (account) {
      if (toAppearance(account) !== toAppearance(local)) keep(account);
    } else if (toAppearance(local) !== toAppearance(DEFAULT)) {
      api.patch('/me', { appearance: toAppearance(local) }).catch(() => { /* try again next visit */ });
    }
  }, [id, saved]);
  return null;
}
