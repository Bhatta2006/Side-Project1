// No 'use client': the root layout (a server component) inlines this script in <head>.
export const PALETTE_KEY = 'socrat:palette';

/** The learner's palettes. Anything else saved (the retired Daybreak ones) falls back to Classic. */
export const PALETTE_IDS = ['classic', 'tide', 'lilac', 'meadow', 'riso', 'dusk'] as const;

/**
 * Runs in <head> before the body paints: the same logic as readPalette + applyPalette, in plain ES5.
 * The look is always "paper": the notebook colours with frames drawn in CSS (no ink frame per element).
 * With nothing saved, the page is Classic in light.
 */
export const PALETTE_BOOT_SCRIPT = `try{var p=JSON.parse(localStorage.getItem('${PALETTE_KEY}')||'null')||{},d=document.documentElement,m=p.mode||'light',k=m==='dark'||(m==='system'&&matchMedia('(prefers-color-scheme: dark)').matches),c=${JSON.stringify(PALETTE_IDS)}.indexOf(p.palette)>=0?p.palette:'classic';if(c!=='classic'||k)d.setAttribute('data-palette',c);if(k)d.setAttribute('data-mode','dark');d.setAttribute('data-look','paper')}catch(e){document.documentElement.setAttribute('data-look','paper')}`;
