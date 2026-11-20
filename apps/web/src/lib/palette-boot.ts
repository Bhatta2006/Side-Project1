// No 'use client': the root layout (a server component) inlines this script in <head>.
export const PALETTE_KEY = 'socrat:palette';

/** The palettes of the Daybreak look (app/daybreak.css). Any other palette is a notebook palette. */
export const DAYBREAK_PALETTE_IDS = ['daybreak', 'ruby', 'ocean', 'lagoon', 'sunset', 'berry'] as const;

/**
 * Runs in <head> before the body paints: the same logic as readPalette + applyPalette, in plain ES5.
 * With nothing saved, the page is Daybreak in light.
 */
export const PALETTE_BOOT_SCRIPT = `try{var p=JSON.parse(localStorage.getItem('${PALETTE_KEY}')||'null')||{},d=document.documentElement,m=p.mode||'light',k=m==='dark'||(m==='system'&&matchMedia('(prefers-color-scheme: dark)').matches),c=p.palette||'daybreak',b=${JSON.stringify(DAYBREAK_PALETTE_IDS)}.indexOf(c)>=0;if(c!=='classic'||k)d.setAttribute('data-palette',c);if(k)d.setAttribute('data-mode','dark');d.setAttribute('data-look',b?'daybreak':'notebook')}catch(e){document.documentElement.setAttribute('data-look','daybreak')}`;
