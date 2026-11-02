'use client';

import { Component, type ReactNode } from 'react';
import Markdown from '@/components/markdown';

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

type Renderer = (props: { params: Record<string, any>; spec: VisualizationSpec }) => ReactNode;

/** Renderers available in the browser. Add a component here when a manifest is registered on the server. */
const RENDERERS: Record<string, Renderer> = {
  markdown: ({ params }) => <Markdown source={String(params.body ?? '')} />,
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

export function VisualizationHost({ spec }: { spec: VisualizationSpec }) {
  const render = RENDERERS[spec.renderer];
  if (!render) return <Fallback spec={spec} />;
  return (
    <figure className="my-4">
      <Guard spec={spec}>
        <div aria-label={spec.alt_text}>{render({ params: spec.params, spec })}</div>
      </Guard>
      <figcaption className="mt-1 text-[13px] text-muted-foreground">{spec.purpose}</figcaption>
    </figure>
  );
}
