import { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import ReactFlow, {
  Controls,
  Background,
  Handle,
  Position,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow';
import type { Node, Edge, NodeProps } from 'reactflow';
import 'reactflow/dist/style.css';
import { orgDataApi, metricsApi } from '../services/api';
import type { HierarchyNode, ManagerSpanAssessment } from '../types';
import { PageHeader, Chip, BenchmarkPill, EmptyState, Loading, formatMoney } from '../components/ui';

type Overlay = 'department' | 'span' | 'cost' | 'grade';

// Muted categorical palette (red is reserved for the accent / attention)
const CATEGORY_COLORS = ['#2D3748', '#9C6B72', '#257A55', '#B97F24', '#6B7FA3', '#8A6F4E', '#5E8C8A', '#4A5568'];
const OTHER_COLOR = '#B8B0A6';
const SPAN_COLORS = { below: '#B97F24', within: '#257A55', above: '#B02E2E' };

const NODE_W = 208;
const NODE_H = 76;
const LEAF_H = 50;
const GAP_X = 28;
const GAP_Y = 64;
const LEAF_GAP = 8;

/** Everything the chart and side panel need about one person. */
interface Person {
  id: string;
  name: string;
  title: string;
  department: string;
  grade: string;
  salary: number;
  layer: number;
  span: number;
  teamSize: number; // everyone below
  teamCost: number; // own + everyone below
  children: Person[];
  parent?: Person;
  singleReport: boolean;
  inSingleChain: boolean; // part of two or more consecutive single-report managers
  assessment?: ManagerSpanAssessment;
}

function buildPeople(root: HierarchyNode, assessments: Map<string, ManagerSpanAssessment>): Person {
  const make = (h: HierarchyNode, layer: number, parent?: Person): Person => {
    const id = h.id ?? h.name;
    const p: Person = {
      id,
      name: h.name,
      title: h.data?.job_title ?? '',
      department: h.data?.department ?? '',
      grade: h.data?.grade ?? '',
      salary: Number(h.data?.salary ?? 0),
      layer,
      span: h.children?.length ?? 0,
      teamSize: 0,
      teamCost: 0,
      children: [],
      parent,
      singleReport: (h.children?.length ?? 0) === 1,
      inSingleChain: false,
      assessment: assessments.get(id),
    };
    p.children = (h.children ?? []).map((c) => make(c, layer + 1, p));
    p.teamSize = p.children.reduce((n, c) => n + 1 + c.teamSize, 0);
    p.teamCost = p.salary + p.children.reduce((n, c) => n + c.teamCost, 0);
    return p;
  };
  // A synthetic "Organization" root (several tops) is not a real layer
  const isSynthetic = root.id === '__org_root__';
  const tree = make(root, isSynthetic ? 0 : 1);
  // Mark chains: a single-report manager whose only report also has exactly one report
  const mark = (p: Person) => {
    if (p.singleReport && p.children[0]?.singleReport) {
      p.inSingleChain = true;
      p.children[0].inSingleChain = true;
    }
    p.children.forEach(mark);
  };
  mark(tree);
  return tree;
}

function flatten(p: Person, out: Person[] = []): Person[] {
  out.push(p);
  p.children.forEach((c) => flatten(c, out));
  return out;
}

/** Tidy tree: managers centred over their teams; teams of individual contributors stack in one column. */
function layout(root: Person, expanded: Set<string>) {
  const nodes: Array<{ person: Person; x: number; y: number; leaf: boolean }> = [];
  const edges: Array<{ from: string; to: string; stacked: boolean }> = [];

  // Returns [width taken, this node's own x]
  const place = (p: Person, x0: number, y: number): [number, number] => {
    const kids = expanded.has(p.id) ? p.children : [];
    if (kids.length === 0) {
      nodes.push({ person: p, x: x0, y, leaf: p.children.length === 0 });
      return [NODE_W, x0];
    }
    const allLeaves = kids.every((k) => k.children.length === 0);
    if (allLeaves && kids.length > 2) {
      nodes.push({ person: p, x: x0, y, leaf: false });
      kids.forEach((k, i) => {
        nodes.push({ person: k, x: x0 + 24, y: y + NODE_H + GAP_Y / 2 + i * (LEAF_H + LEAF_GAP), leaf: true });
        edges.push({ from: p.id, to: k.id, stacked: true });
      });
      return [NODE_W + 24, x0];
    }
    let cursor = x0;
    const childXs: number[] = [];
    kids.forEach((k, i) => {
      const [w, childX] = place(k, cursor, y + NODE_H + GAP_Y);
      childXs.push(childX);
      edges.push({ from: p.id, to: k.id, stacked: false });
      cursor += w + (i < kids.length - 1 ? GAP_X : 0);
    });
    const x = (childXs[0] + childXs[childXs.length - 1]) / 2;
    nodes.push({ person: p, x, y, leaf: false });
    return [Math.max(cursor - x0, NODE_W), x];
  };
  place(root, 0, 0);
  return { nodes, edges };
}

interface ChartNodeData {
  person: Person;
  leaf: boolean;
  stripe: string;
  overlayLabel: string;
  flags: boolean;
  selected: boolean;
  expanded: boolean;
  onToggle: (id: string) => void;
}

function PersonNode({ data }: NodeProps<ChartNodeData>) {
  const { person, leaf, stripe, overlayLabel, flags, selected, expanded, onToggle } = data;
  const height = leaf ? LEAF_H : NODE_H;
  return (
    <div
      className="relative overflow-hidden rounded-[2px] border bg-white text-left transition-colors"
      style={{ width: NODE_W, height, borderColor: selected ? 'var(--color-primary)' : 'var(--color-hairline)', boxShadow: selected ? '0 0 0 1px var(--color-primary)' : 'none' }}
    >
      <Handle type="target" position={leaf ? Position.Left : Position.Top} style={{ opacity: 0 }} />
      <span className="absolute inset-x-0 top-0 h-[3px]" style={{ background: stripe }} />
      <div className="px-3 pt-2.5">
        <p className="truncate text-[12.5px] font-semibold text-ink" title={person.name}>{person.name}</p>
        <p className="truncate text-[11.5px] text-secondary" title={person.title}>{person.title}</p>
        {!leaf && (
          <p className="mt-0.5 flex items-center justify-between text-[11.5px] text-faint">
            <span className="truncate">{overlayLabel}</span>
            {person.children.length > 0 && (
              <button
                onClick={(e) => { e.stopPropagation(); onToggle(person.id); }}
                className="ml-2 shrink-0 font-semibold text-primary-600 hover:text-primary-700"
                aria-label={expanded ? `Collapse ${person.name}'s team` : `Expand ${person.name}'s team`}
              >
                {expanded ? '–' : `+${person.span}`}
              </button>
            )}
          </p>
        )}
      </div>
      {flags && person.singleReport && (
        <span
          className="absolute right-1.5 top-1.5 rounded-full border px-1.5 text-[10.5px] font-semibold"
          style={{ borderColor: 'var(--color-score-amber)', color: 'var(--color-score-amber)', background: '#fff' }}
          title={person.inSingleChain ? 'Part of a chain of single-report managers — strong layer-removal candidate' : 'Manages one person — layer-removal candidate'}
        >
          {person.inSingleChain ? '1:1 chain' : '1 report'}
        </span>
      )}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { person: PersonNode };

function OrgChartInner() {
  const [root, setRoot] = useState<Person | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overlay, setOverlay] = useState<Overlay>('department');
  const [flags, setFlags] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [searchMiss, setSearchMiss] = useState(false);
  const { setCenter, fitView } = useReactFlow();

  useEffect(() => {
    Promise.all([orgDataApi.getLatest(), metricsApi.getLatest().catch(() => null)])
      .then(([org, metrics]) => {
        const hierarchy = org.hierarchy as unknown as HierarchyNode;
        if (!hierarchy || !hierarchy.name) {
          setError('No reporting lines found in this upload.');
          return;
        }
        const assessments = new Map(
          (metrics?.metrics.span_of_control.manager_assessments ?? []).map((a) => [a.manager_id, a])
        );
        const tree = buildPeople(hierarchy, assessments);
        setRoot(tree);
        setSelectedId(tree.id);
        // Open the top two layers: readable at a glance; deeper teams are one click away
        const open = new Set<string>();
        flatten(tree).forEach((p) => { if (p.layer <= 1 && p.children.length) open.add(p.id); });
        setExpanded(open);
      })
      .catch(() => setError('Upload an org structure CSV to see the org chart.'))
      .finally(() => setLoading(false));
  }, []);

  const people = useMemo(() => (root ? flatten(root) : []), [root]);
  const byId = useMemo(() => new Map(people.map((p) => [p.id, p])), [people]);

  // Colour keys built from the data itself (no hard-coded grades)
  const departmentColors = useMemo(() => {
    const counts = new Map<string, number>();
    people.forEach((p) => counts.set(p.department, (counts.get(p.department) ?? 0) + 1));
    const ordered = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([d]) => d);
    return new Map(ordered.map((d, i) => [d, i < CATEGORY_COLORS.length ? CATEGORY_COLORS[i] : OTHER_COLOR]));
  }, [people]);
  const gradeColors = useMemo(() => {
    const layerSum = new Map<string, { sum: number; n: number }>();
    people.forEach((p) => {
      const v = layerSum.get(p.grade) ?? { sum: 0, n: 0 };
      layerSum.set(p.grade, { sum: v.sum + p.layer, n: v.n + 1 });
    });
    const ordered = [...layerSum.entries()].sort((a, b) => a[1].sum / a[1].n - b[1].sum / b[1].n).map(([g]) => g);
    // Seniority as a sequential ink scale: most senior darkest
    return new Map(ordered.map((g, i) => [g, `rgba(28,31,36,${1 - (0.8 * i) / Math.max(1, ordered.length - 1)})`]));
  }, [people]);
  const maxTeamCost = useMemo(() => Math.max(1, ...people.filter((p) => p.children.length).map((p) => p.teamCost)), [people]);

  const overlayFor = useCallback(
    (p: Person): { stripe: string; label: string } => {
      switch (overlay) {
        case 'department':
          return { stripe: departmentColors.get(p.department) ?? OTHER_COLOR, label: p.department };
        case 'grade':
          return { stripe: gradeColors.get(p.grade) ?? OTHER_COLOR, label: `Grade ${p.grade}` };
        case 'cost':
          return {
            stripe: p.children.length ? `rgba(196,30,58,${0.15 + 0.85 * (p.teamCost / maxTeamCost)})` : 'var(--color-hairline)',
            label: p.children.length ? `Team cost ${formatMoney(p.teamCost)}` : formatMoney(p.salary),
          };
        case 'span': {
          const a = p.assessment;
          if (!a) return { stripe: 'var(--color-hairline)', label: p.children.length ? `${p.span} reports` : '' };
          const glyph = { below: '↓', within: '✓', above: '↑' }[a.status];
          return { stripe: SPAN_COLORS[a.status], label: `${glyph} ${a.span} reports · ${a.benchmark_range[0]}–${a.benchmark_range[1]}` };
        }
      }
    },
    [overlay, departmentColors, gradeColors, maxTeamCost]
  );

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const { nodes, edges } = useMemo(() => {
    if (!root) return { nodes: [] as Node[], edges: [] as Edge[] };
    const laid = layout(root, expanded);
    const rfNodes: Node<ChartNodeData>[] = laid.nodes.map(({ person, x, y, leaf }) => {
      const o = overlayFor(person);
      return {
        id: person.id,
        type: 'person',
        position: { x, y },
        draggable: false,
        data: {
          person, leaf, stripe: o.stripe, overlayLabel: o.label, flags,
          selected: person.id === selectedId, expanded: expanded.has(person.id), onToggle: toggle,
        },
      };
    });
    const rfEdges: Edge[] = laid.edges.map((e) => ({
      id: `${e.from}->${e.to}`,
      source: e.from,
      target: e.to,
      type: 'smoothstep',
      style: { stroke: '#CFC6BB', strokeWidth: 1.2 },
    }));
    return { nodes: rfNodes, edges: rfEdges };
  }, [root, expanded, overlayFor, flags, selectedId, toggle]);

  const expandTo = (p: Person) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      let cur = p.parent;
      while (cur) { next.add(cur.id); cur = cur.parent; }
      return next;
    });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim().toLowerCase();
    if (!q) return;
    const match = people.find((p) => p.name.toLowerCase().includes(q)) ?? people.find((p) => p.title.toLowerCase().includes(q));
    setSearchMiss(!match);
    if (!match) return;
    expandTo(match);
    setSelectedId(match.id);
    // Wait for the re-layout, then centre on the person
    setTimeout(() => {
      const laid = layout(root!, new Set([...expanded, ...ancestorIds(match)]));
      const pos = laid.nodes.find((n) => n.person.id === match.id);
      if (pos) setCenter(pos.x + NODE_W / 2, pos.y + NODE_H / 2, { zoom: 1, duration: 400 });
    }, 50);
  };

  if (loading) return <Loading label="Drawing the reporting lines" />;
  if (error || !root) {
    return (
      <>
        <PageHeader eyebrow="01 · Diagnose — org chart" title="Org chart" />
        <EmptyState title="No reporting lines yet" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} />
      </>
    );
  }

  const selected = (selectedId && byId.get(selectedId)) || root;
  const managerCount = people.filter((p) => p.children.length).length;
  const singles = people.filter((p) => p.singleReport).length;
  const chainCount = people.filter((p) => p.inSingleChain && p.singleReport).length;
  const legend: Array<[string, string]> =
    overlay === 'department'
      ? [...departmentColors.entries()].slice(0, CATEGORY_COLORS.length).map(([d, c]) => [d, c])
      : overlay === 'grade'
        ? [...gradeColors.entries()].map(([g, c]) => [g, c])
        : overlay === 'span'
          ? [['↓ Below benchmark', SPAN_COLORS.below], ['✓ Within', SPAN_COLORS.within], ['↑ Above', SPAN_COLORS.above]]
          : [['Lighter = smaller team cost', 'rgba(196,30,58,.25)'], ['Darker = larger team cost', 'rgba(196,30,58,1)']];

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — org chart"
        title={singles ? `${singles} of ${managerCount} managers have a single direct report` : `${managerCount} managers across ${people.length} people`}
        lede={
          chainCount
            ? `${chainCount} of them sit in chains of single-report managers — the clearest candidates for removing a layer. Click a manager's + to open their team.`
            : 'Click a manager\'s + to open their team. Switch the overlay to see departments, spans, cost or grades.'
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="label mb-0 mr-1">Colour by</span>
        {([['department', 'Department'], ['span', 'Span vs benchmark'], ['cost', 'Team cost'], ['grade', 'Grade']] as const).map(([k, label]) => (
          <Chip key={k} active={overlay === k} onClick={() => setOverlay(k)}>{label}</Chip>
        ))}
        <label className="ml-3 flex items-center gap-2 text-sm text-secondary">
          <input type="checkbox" checked={flags} onChange={(e) => setFlags(e.target.checked)} className="accent-[#C41E3A]" />
          Flag layer-removal candidates
        </label>
        <form onSubmit={handleSearch} className="ml-auto flex items-center gap-2">
          <input
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSearchMiss(false); }}
            placeholder="Find a person or title"
            className="input w-56 py-1.5 text-sm"
            aria-label="Find a person or title"
          />
          <button type="submit" className="btn btn-quiet py-1.5">Find</button>
        </form>
      </div>
      {searchMiss && <p className="mb-3 text-sm text-faint">No one matches “{query}”.</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="card relative h-[640px] p-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, n) => setSelectedId(n.id)}
            fitView
            fitViewOptions={{ padding: 0.15, maxZoom: 1 }}
            minZoom={0.15}
            nodesConnectable={false}
            proOptions={{ hideAttribution: true }}
          >
            <Controls showInteractive={false} />
            <Background color="#E7E0D8" gap={20} size={1} />
          </ReactFlow>
          <div className="absolute bottom-3 right-3 flex gap-2">
            <button className="btn btn-quiet bg-white py-1 text-xs" onClick={() => { setExpanded(new Set(people.filter((p) => p.children.length).map((p) => p.id))); setTimeout(() => fitView({ padding: 0.1, duration: 300 }), 50); }}>Expand all</button>
            <button className="btn btn-quiet bg-white py-1 text-xs" onClick={() => { setExpanded(new Set(people.filter((p) => p.layer <= 2 && p.children.length).map((p) => p.id))); setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50); }}>Top 3 layers</button>
          </div>
        </div>

        {/* Side panel: always shows someone (Playbook: panel beside, never a modal) */}
        <aside className="card self-start">
          <p className="eyebrow eyebrow-faint mb-2">Selected</p>
          <h2 className="text-[22px] leading-tight">{selected.name}</h2>
          <p className="mt-1 text-sm text-secondary">{selected.title}</p>
          <dl className="mt-5 divide-y divide-hairline border-y border-hairline text-sm">
            {[
              ['Department', selected.department || '—'],
              ['Grade', selected.grade || '—'],
              ['Layer', selected.layer || '—'],
              ['Direct reports', selected.span],
              ['Everyone below', selected.teamSize],
              ['Team cost', formatMoney(selected.teamCost)],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between gap-4 py-2">
                <dt className="text-faint">{k}</dt>
                <dd className="tabular text-right font-medium text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          {selected.assessment && (
            <div className="mt-4 text-sm">
              <div className="flex items-center gap-2">
                <BenchmarkPill status={selected.assessment.status} />
                <span className="text-secondary">
                  benchmark {selected.assessment.benchmark_range[0]}–{selected.assessment.benchmark_range[1]} {selected.assessment.work_type === 'operational' ? 'for frontline operational managers' : 'for managers not tagged Operational'}
                </span>
              </div>
              <p className="mt-1 text-xs text-faint">Why: {selected.assessment.work_type_basis}</p>
            </div>
          )}
          {selected.singleReport && (
            <p className="mt-4 text-sm text-secondary">
              <span className="font-semibold" style={{ color: 'var(--color-score-amber)' }}>Layer-removal candidate.</span>{' '}
              {selected.inSingleChain ? 'Part of a chain of managers who each manage one person.' : 'Manages one person.'}
            </p>
          )}
          {selected.children.length > 0 && (
            <div className="mt-5">
              <p className="label">Direct reports</p>
              <ul className="max-h-56 space-y-1 overflow-auto text-sm">
                {selected.children.map((c) => (
                  <li key={c.id}>
                    <button onClick={() => { expandTo(c); setSelectedId(c.id); }} className="text-left text-ink hover:text-primary-600">
                      {c.name} <span className="text-faint">· {c.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {selected.parent && (
            <button onClick={() => setSelectedId(selected.parent!.id)} className="mt-5 text-sm font-semibold text-primary-600">
              ↑ Reports to {selected.parent.name}
            </button>
          )}
        </aside>
      </div>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-secondary">
        {legend.map(([label, color]) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className="inline-block h-[3px] w-5" style={{ background: color }} />
            {label}
          </span>
        ))}
        {overlay === 'department' && departmentColors.size > CATEGORY_COLORS.length && (
          <span className="flex items-center gap-1.5"><span className="inline-block h-[3px] w-5" style={{ background: OTHER_COLOR }} />Other departments</span>
        )}
      </div>
    </>
  );
}

function ancestorIds(p: Person): string[] {
  const ids: string[] = [];
  let cur = p.parent;
  while (cur) { ids.push(cur.id); cur = cur.parent; }
  return ids;
}

export default function OrgChart() {
  return (
    <ReactFlowProvider>
      <OrgChartInner />
    </ReactFlowProvider>
  );
}
