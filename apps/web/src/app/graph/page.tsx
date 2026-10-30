'use client';

import '@xyflow/react/dist/style.css';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Background, Controls, Handle, MarkerType, Position, ReactFlow, type Edge, type Node, type NodeProps } from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import { useTheme } from 'next-themes';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, conceptHref } from '@/lib/routes';
import type { PlanView, RoadmapItem } from '@/lib/types';
import { ErrorNote, Loading, Page } from '@/components/common';
import { StatusIcon, StatusLegend, statusFromRoadmap } from '@/components/socrat/status';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const W = 220;
const H = 72;

type SkillData = { item: RoadmapItem; module: string; current: boolean };
type SkillNode = Node<SkillData, 'skill'>;

/** Concepts the plan has set aside or dropped stay on the map, faded, so a change is visible. */
const ASIDE = ['optional', 'skipped'];
const faded = (i: RoadmapItem) => ASIDE.includes(i.status) || i.deferred;

function Skill({ data }: NodeProps<SkillNode>) {
  const { item, module, current } = data;
  const status = item.review_due && item.status !== 'locked' ? 'review' : statusFromRoadmap(item);
  const note = item.transfer === 'verified' ? 'Transfer verified' : item.status === 'skipped' ? 'Dropped' : item.status === 'optional' ? 'Optional' : item.deferred ? 'Set aside' : item.priority ? 'Focus' : '';
  return (
    <>
      <Handle type="target" position={Position.Left} isConnectable={false} className="!opacity-0" />
      <Link
        href={conceptHref(item.concept)}
        className={cn('flex items-center gap-3 rounded-[16px] border bg-card px-3 py-2 text-left shadow-sm', current && 'ring-2 ring-primary', faded(item) && 'opacity-50')}
        style={{ width: W, height: H }}
      >
        <StatusIcon status={status} size={32} className="flex-none" />
        <span className="min-w-0">
          <span className="block line-clamp-2 text-[13px] leading-4 font-semibold">{item.title}</span>
          <span className="block truncate text-[11px] text-muted-foreground">{note ? `${note} · ` : ''}{module}</span>
        </span>
      </Link>
      <Handle type="source" position={Position.Right} isConnectable={false} className="!opacity-0" />
    </>
  );
}
const nodeTypes = { skill: Skill };

/** Prerequisite edges between concepts still in the enrolled roadmap, laid out left to right. */
function layout(plan: PlanView): { nodes: SkillNode[]; edges: Edge[] } {
  const items = plan.modules.flatMap(m => m.concepts.map(c => ({ c, module: m.title })));
  const ids = new Set(items.map(x => x.c.concept));
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'LR', nodesep: 24, ranksep: 70 });
  const edges: Edge[] = [];
  for (const { c } of items) {
    g.setNode(c.concept, { width: W, height: H });
    for (const p of c.requires.filter(r => ids.has(r))) {
      g.setEdge(p, c.concept);
      const dim = faded(c) || ASIDE.includes(items.find(x => x.c.concept === p)!.c.status);
      edges.push({
        id: `${p}>${c.concept}`,
        source: p,
        target: c.concept,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: dim ? { strokeDasharray: '4 4', opacity: 0.5 } : undefined,
      });
    }
  }
  dagre.layout(g);
  const nodes = items.map<SkillNode>(({ c, module }) => {
    const { x, y } = g.node(c.concept);
    return { id: c.concept, type: 'skill', position: { x: x - W / 2, y: y - H / 2 }, data: { item: c, module, current: c.concept === plan.current_concept } };
  });
  return { nodes, edges };
}

export default function GraphPage() {
  const allowed = useGuard('active');
  const { resolvedTheme } = useTheme();
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    api.get<PlanView>('/plan').then(setPlan).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  const graph = useMemo(() => (plan ? layout(plan) : null), [plan]);

  if (!allowed || (!plan && !error)) return <Loading label="Loading your skill graph" />;
  if (!plan || !graph) return <Page><ErrorNote message={error} retry={load} /></Page>;

  return (
    <Page wide>
      <header className="mb-6">
        <h1 className="type-display-l">Your skill <span className="hl hl-draw">graph</span></h1>
        <p className="mt-3 max-w-2xl text-base text-muted-foreground">
          Each arrow points from a skill to what it unlocks. The graph is rebuilt from your results each time, so when Socrat adds, repairs or sets aside a skill, it changes here. Faded skills are optional or set aside.
        </p>
        <Button asChild variant="outline" className="mt-4"><Link href="/plan">Back to {NAME.skills}</Link></Button>
      </header>
      <div className="h-[70vh] min-h-96 overflow-hidden rounded-card border" role="group" aria-label="Skill graph. The Skills page lists the same skills in order.">
        <ReactFlow
          nodes={graph.nodes}
          edges={graph.edges}
          nodeTypes={nodeTypes}
          colorMode={resolvedTheme === 'dark' ? 'dark' : 'light'}
          nodesDraggable={false}
          nodesConnectable={false}
          fitView
          minZoom={0.2}
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="mt-4"><StatusLegend only={['not_seen', 'read', 'assumed', 'practised', 'mastered', 'review', 'locked']} /></div>
    </Page>
  );
}
