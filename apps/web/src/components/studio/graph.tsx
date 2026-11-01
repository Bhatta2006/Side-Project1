'use client';

import { useEffect, useRef } from 'react';

/** The formula syntax the course builder uses, in JSXGraph's JessieCode (which never runs JavaScript). */
function jessie(expression: string) {
  return expression.replace(/\bln\(/g, 'log(').replace(/\bpi\b/g, 'PI');
}

const FUNCTIONS = new Set(['sin', 'cos', 'tan', 'exp', 'ln', 'sqrt', 'pi', 'log', 'abs']);

/** Single letters other than x that a plot uses become sliders the learner can drag. */
export function parametersOf(expressions: string[]): string[] {
  const found = new Set<string>();
  for (const e of expressions) {
    for (const word of e.match(/[a-z]+/gi) ?? []) {
      if (word.length === 1 && word !== 'x' && word !== 'e' && !FUNCTIONS.has(word)) found.add(word);
    }
  }
  return [...found].sort().slice(0, 3);
}

type Board = { create: (t: string, a: unknown[], o?: object) => unknown; removeObject: (o: unknown) => void };

/** Draws functions of x. JSXGraph is MIT/LGPL licensed and loaded only when a graph is shown. */
export function Graph({ expressions, label, mine, points, onFit }: { expressions: string[]; label: string; mine?: string; points?: [number, number][]; onFit?: (slope: number, intercept: number) => void }) {
  const host = useRef<HTMLDivElement>(null);
  const board = useRef<Board | null>(null);
  const curve = useRef<unknown>(null);

  useEffect(() => {
    const element = host.current;
    if (!element || (!expressions.length && !points?.length)) return;
    let raw: unknown = null;
    let stopped = false;
    import('jsxgraph').then(module => {
      if (stopped) return;
      const JXG = (module as unknown as { default?: typeof module }).default ?? module;
      const jsx = JXG as unknown as {
        JSXGraph: { initBoard: (el: HTMLElement, o: object) => { create: (t: string, a: unknown[], o?: object) => unknown }; freeBoard: (b: unknown) => void };
      };
      const reach = Math.max(6, ...(points ?? []).flatMap(([x, y]) => [Math.abs(x), Math.abs(y)]).map(v => Math.ceil(v * 1.3)));
      const created = jsx.JSXGraph.initBoard(element, {
        boundingbox: [-reach, reach, reach, -reach], axis: true, showCopyright: false, showNavigation: false,
        pan: { enabled: true }, zoom: { wheel: false, pinch: true },
      });
      raw = created;
      board.current = created as unknown as Board;
      if (points?.length) {
        // Data to fit, and a line the learner positions by dragging two handles (snapped to half units).
        points.forEach(([x, y]) => { try { created.create('point', [x, y], { fixed: true, size: 4, name: '', strokeColor: '#0d9488', fillColor: '#0d9488' }); } catch { /* skip */ } });
        try {
          const grab = { size: 6, name: '', snapToGrid: true, snapSizeX: 0.5, snapSizeY: 0.5, strokeColor: '#e11d48', fillColor: '#e11d48' };
          const a = created.create('point', [-reach / 3, 0], grab) as { X: () => number; Y: () => number };
          const b = created.create('point', [reach / 3, 0.5], grab) as { X: () => number; Y: () => number };
          created.create('line', [a, b], { strokeColor: '#e11d48', strokeWidth: 2, dash: 2 });
          const report = () => {
            const dx = b.X() - a.X();
            if (Math.abs(dx) < 1e-9) return;
            const slope = (b.Y() - a.Y()) / dx;
            onFit?.(Number(slope.toFixed(3)), Number((a.Y() - slope * a.X()).toFixed(3)));
          };
          (created as unknown as { on: (e: string, f: () => void) => void }).on('update', report);
          report();
        } catch { /* the data stays visible without the handles */ }
      }
      parametersOf(expressions).forEach((name, i) => {
        try { created.create('slider', [[-5.5, 5.2 - i * 0.9], [-1.5, 5.2 - i * 0.9], [-5, 1, 5]], { name, snapWidth: 0.1, withLabel: true }); }
        catch { /* a missing slider leaves the parameter at its default */ }
      });
      const colors = ['#4f46e5', '#0d9488', '#d97706'];
      expressions.forEach((e, i) => {
        try { created.create('functiongraph', [jessie(e)], { strokeColor: colors[i % colors.length], strokeWidth: 2 }); }
        catch { /* an expression the board cannot draw is simply left off */ }
      });
    }).catch(() => { /* the graph is a help, never required */ });
    return () => {
      stopped = true;
      board.current = null;
      curve.current = null;
      if (raw) {
        import('jsxgraph').then(module => {
          const JXG = (module as unknown as { default?: typeof module }).default ?? module;
          (JXG as unknown as { JSXGraph: { freeBoard: (b: unknown) => void } }).JSXGraph.freeBoard(raw);
        }).catch(() => {});
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expressions, points]);

  // The learner's own answer, drawn as they type, so they can see how it compares.
  useEffect(() => {
    const b = board.current;
    if (!b) return;
    if (curve.current) { try { b.removeObject(curve.current); } catch { /* already gone */ } curve.current = null; }
    if (!mine?.trim() || /[=,;]/.test(mine) || mine.length > 120) return;
    try { curve.current = b.create('functiongraph', [jessie(mine.replace(/(\d)([a-z(])/gi, '$1*$2'))], { strokeColor: '#e11d48', strokeWidth: 2, dash: 2 }); }
    catch { /* half-typed input is expected */ }
  }, [mine, expressions]);

  if (!expressions.length && !points?.length) return null;
  return <div ref={host} role="img" aria-label={label} className="jxgbox h-64 w-full max-w-xl rounded-md border" />;
}
