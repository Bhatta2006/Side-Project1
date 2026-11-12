'use client';
// One copy of each Soc drawing per page. Inside <SocSprite>, a Soc at rest (eyes centred) draws
// nothing itself: it registers its drawing here and points at it with <use>. The drawings are
// written once, as <symbol>s, in a hidden <svg> after the page's content. A busy page (the landing
// has dozens of small Socs, many wearing the same face) then carries each face once.
//
// Only drawings registered inside <SocSpriteEager> (the first screen) are written into the server
// HTML. The rest are added straight after hydration, before the reader can scroll to them: a Soc
// drawing is 20-30 KB of path data, and the page should not wait on faces nobody can see yet.
import * as React from 'react';

export type SpriteDrawing = { w: number; h: number; svg: string };

type Store = {
  defs: Map<string, SpriteDrawing>;
  /** Drawings the server HTML must carry: the ones used on the first screen. */
  eager: Set<string>;
  /** How many drawings the hidden <svg> has written out. */
  emitted: number;
  version: number;
  listeners: Set<() => void>;
};

const SpriteContext = React.createContext<Store | null>(null);
const EagerContext = React.createContext(false);

/** Wraps what is on screen at first paint, so its Socs are drawn into the server HTML. */
export function SocSpriteEager({ children }: { children: React.ReactNode }) {
  return <EagerContext.Provider value>{children}</EagerContext.Provider>;
}

/**
 * Inside a <SocSprite>, a function that registers a drawing under a symbol id. Registering during
 * render is safe: a drawing is fully determined by its id, and the defs render after every Soc on
 * the server and during hydration, so both see the same set.
 */
export function useSocSprite(): ((id: string, draw: () => SpriteDrawing) => SpriteDrawing) | null {
  const store = React.useContext(SpriteContext);
  const eager = React.useContext(EagerContext);
  // A drawing first seen after hydration (a new mood) is written out before the browser paints.
  React.useLayoutEffect(() => {
    if (!store || store.defs.size <= store.emitted) return;
    store.version++;
    store.listeners.forEach(fn => fn());
  });
  if (!store) return null;
  return (id, draw) => {
    let drawing = store.defs.get(id);
    if (!drawing) {
      drawing = draw();
      store.defs.set(id, drawing);
    }
    if (eager) store.eager.add(id);
    return drawing;
  };
}

const noSubscribe = () => () => {};

function SpriteDefs({ store }: { store: Store }) {
  const subscribe = React.useCallback((fn: () => void) => {
    store.listeners.add(fn);
    return () => { store.listeners.delete(fn); };
  }, [store]);
  const snapshot = React.useCallback(() => store.version, [store]);
  React.useSyncExternalStore(subscribe, snapshot, snapshot);
  // The server and the hydrating client write the first screen's drawings; then all of them.
  const all = React.useSyncExternalStore(noSubscribe, () => true, () => false);
  const entries = [...store.defs].filter(([id]) => all || store.eager.has(id));
  store.emitted = all ? entries.length : 0;
  // Not display:none, which stops some browsers resolving the ids inside the symbols.
  return (
    <svg aria-hidden="true" focusable="false" width="0" height="0" style={{ position: 'absolute', width: 0, height: 0, overflow: 'hidden' }}>
      {entries.map(([id, d]) => (
        <symbol key={id} id={id} viewBox={`0 0 ${d.w} ${d.h}`} overflow="visible" dangerouslySetInnerHTML={{ __html: d.svg }} />
      ))}
    </svg>
  );
}

export function SocSprite({ children }: { children: React.ReactNode }) {
  const [store] = React.useState<Store>(() => ({ defs: new Map(), eager: new Set(), emitted: 0, version: 0, listeners: new Set() }));
  return (
    <SpriteContext.Provider value={store}>
      {children}
      <SpriteDefs store={store} />
    </SpriteContext.Provider>
  );
}
