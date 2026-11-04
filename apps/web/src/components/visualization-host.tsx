'use client';

import dynamic from 'next/dynamic';
import { Component, useState, type ReactNode } from 'react';
import Markdown from '@/components/markdown';
import { Graph } from '@/components/studio/graph';
import { CodeTask } from '@/components/visuals/code-task';
import { Simulation } from '@/components/visuals/simulation';
import { Timeline } from '@/components/visuals/timeline';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/lib/i18n';
import { useLite } from '@/lib/lite';

/**
 * Renders a lesson's typed VisualizationSpec through approved components only. The spec is data:
 * a renderer id plus validated params. An unknown renderer, a crash, or a renderer that is not
 * wired in this build all end in the same place: the spec's own fallback text and description.
 * Nothing here ever evaluates model-written code.
 */
export type VisualizationSpec = {
  renderer: string;
  version: string;
  params: Record<string, unknown>;
  purpose: string;
  fallback_text: string;
  alt_text: string;
};

type Lesson = { concept: string; title: string };
type Renderer = (props: { params: Record<string, any>; spec: VisualizationSpec; lesson?: Lesson }) => ReactNode;

/** Renderers available in the browser. Add a component here when a manifest is registered on the server. */
const RENDERERS: Record<string, Renderer> = {
  markdown: ({ params }) => <Markdown source={String(params.body ?? '')} />,
  'function-plot': ({ params, spec }) => (
    <Graph expressions={(params.expressions as string[]) ?? []} label={spec.alt_text} />
  ),
  'concept-map': ({ params }) => {
    const nodes: string[] = params.nodes ?? [];
    const edges: [string, string][] = params.edges ?? [];
    return (
      <ul className="space-y-1 text-sm">
        {nodes.map((n) => (
          <li key={n}>
            <span className="font-medium">{n}</span>
            {edges.filter(([, to]) => to === n).length ? (
              <span className="text-muted-foreground">
                {' '}
                after {edges.filter(([, to]) => to === n).map(([from]) => from).join(', ')}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    );
  },
  simulation: ({ params }) => <Simulation params={params as { model: string; inputs?: Record<string, number> }} />,
  timeline: ({ params }) => <Timeline params={params as { unit: string; length: number; tracks: string[] }} />,
  'code-studio': ({ params }) => <CodeTask params={params as { language: string; starter?: string; problem_id?: string | null }} />,
  'playground-visual': ({ lesson }) => (lesson ? <ConceptVisual concept={lesson.concept} title={lesson.title} /> : null),
  'self-check': ({ params }) => (
    <ul className="space-y-2">
      {(params.criteria as string[]).map((c) => (
        <li key={c}>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" />
            {c}
          </label>
        </li>
      ))}
    </ul>
  ),
};

/** Renderers that download a library or call the server on every change; lite mode holds them. */
const HEAVY = new Set(['function-plot', 'simulation', 'playground-visual']);

// The concept's shared Playground visual (sketch or 3D film), loaded only when a lesson has one.
const ConceptVisual = dynamic(() => import('@/components/socrat/concept-visual').then(m => m.ConceptVisual), { ssr: false });

function Fallback({ spec, why }: { spec: VisualizationSpec; why?: string }) {
  return (
    <div role="group" aria-label={spec.alt_text} className="rounded-xl border bg-card p-4 text-sm">
      {why ? <p className="mb-2 text-muted-foreground">{why}</p> : null}
      <Markdown source={spec.fallback_text} />
    </div>
  );
}

class Guard extends Component<{ spec: VisualizationSpec; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <Fallback spec={this.props.spec} why="This visual could not load." /> : this.props.children;
  }
}

export function VisualizationHost({ spec, lesson }: { spec: VisualizationSpec; lesson?: Lesson }) {
  const { lite } = useLite();
  const { t } = useI18n();
  const [requested, setRequested] = useState(false);
  const render = RENDERERS[spec.renderer];
  if (!render) return <Fallback spec={spec} />;
  if (lite && !requested && HEAVY.has(spec.renderer)) {
    return (
      <figure className="my-4">
        <Fallback spec={spec} why={t('lite.visual.held')} />
        <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => setRequested(true)}>
          {t('lite.visual.load')}
        </Button>
        <figcaption className="mt-1 text-[13px] text-muted-foreground">{spec.purpose}</figcaption>
      </figure>
    );
  }
  return (
    <figure className="my-4">
      <Guard spec={spec}>
        <div role="group" aria-label={spec.alt_text}>{render({ params: spec.params, spec, lesson })}</div>
      </Guard>
      <figcaption className="mt-1 text-[13px] text-muted-foreground">{spec.purpose}</figcaption>
    </figure>
  );
}
