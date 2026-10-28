'use client';

import { useEffect, useRef } from 'react';

/** The formula syntax the course builder uses, in JSXGraph's JessieCode (which never runs JavaScript). */
function jessie(expression: string) {
  return expression.replace(/\bln\(/g, 'log(').replace(/\bpi\b/g, 'PI');
}

/** Draws functions of x. JSXGraph is MIT/LGPL licensed and loaded only when a graph is shown. */
export function Graph({ expressions, label }: { expressions: string[]; label: string }) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = host.current;
    if (!element || !expressions.length) return;
    let board: { jc?: unknown } | null = null;
    let stopped = false;
    import('jsxgraph').then(module => {
      if (stopped) return;
      const JXG = (module as unknown as { default?: typeof module }).default ?? module;
      const jsx = JXG as unknown as {
        JSXGraph: { initBoard: (el: HTMLElement, o: object) => { create: (t: string, a: unknown[], o?: object) => unknown }; freeBoard: (b: unknown) => void };
      };
      const created = jsx.JSXGraph.initBoard(element, {
        boundingbox: [-6, 6, 6, -6], axis: true, showCopyright: false, showNavigation: false,
        pan: { enabled: true }, zoom: { wheel: false, pinch: true },
      });
      board = created as unknown as { jc?: unknown };
      const colors = ['#4f46e5', '#0d9488', '#d97706'];
      expressions.forEach((e, i) => {
        try { created.create('functiongraph', [jessie(e)], { strokeColor: colors[i % colors.length], strokeWidth: 2 }); }
        catch { /* an expression the board cannot draw is simply left off */ }
      });
    }).catch(() => { /* the graph is a help, never required */ });
    return () => {
      stopped = true;
      if (board) {
        import('jsxgraph').then(module => {
          const JXG = (module as unknown as { default?: typeof module }).default ?? module;
          (JXG as unknown as { JSXGraph: { freeBoard: (b: unknown) => void } }).JSXGraph.freeBoard(board);
        }).catch(() => {});
      }
    };
  }, [expressions]);

  if (!expressions.length) return null;
  return <div ref={host} role="img" aria-label={label} className="jxgbox h-64 w-full max-w-xl rounded-md border" />;
}
