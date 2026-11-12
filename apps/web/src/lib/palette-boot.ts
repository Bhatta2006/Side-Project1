// No 'use client': the root layout (a server component) inlines this script in <head>.
export const PALETTE_KEY = 'socrat:palette';

/** Runs in <head> before the body paints: the same logic as readPalette + applyPalette, in plain ES5. */
export const PALETTE_BOOT_SCRIPT = `try{var p=JSON.parse(localStorage.getItem('${PALETTE_KEY}')||'null')||{},d=document.documentElement,m=p.mode||'light',k=m==='dark'||(m==='system'&&matchMedia('(prefers-color-scheme: dark)').matches),c=p.palette||'classic';if(c!=='classic'||k)d.setAttribute('data-palette',c);if(k)d.setAttribute('data-mode','dark')}catch(e){}`;
