import { useMemo } from 'react';
import type { StructureDiagram, DiagramNode, DiagramConnection, DiagramNodeType, DiagramConnectionType } from '../types';

interface ArchetypeDiagramProps {
  diagram: StructureDiagram;
  width?: number;
  height?: number;
}

// Node colors by type
const NODE_COLORS: Record<DiagramNodeType, { fill: string; stroke: string; text: string }> = {
  executive: { fill: '#4F46E5', stroke: '#3730A3', text: '#FFFFFF' },
  department: { fill: '#0891B2', stroke: '#0E7490', text: '#FFFFFF' },
  team: { fill: '#059669', stroke: '#047857', text: '#FFFFFF' },
  role: { fill: '#7C3AED', stroke: '#6D28D9', text: '#FFFFFF' },
  external: { fill: '#F59E0B', stroke: '#D97706', text: '#1F2937' },
  shared_service: { fill: '#EC4899', stroke: '#DB2777', text: '#FFFFFF' },
};

// Connection styles by type
const CONNECTION_STYLES: Record<DiagramConnectionType, { stroke: string; strokeDasharray?: string; strokeWidth: number }> = {
  reporting: { stroke: '#374151', strokeWidth: 2 },
  coordination: { stroke: '#3B82F6', strokeDasharray: '5,5', strokeWidth: 1.5 },
  advisory: { stroke: '#10B981', strokeDasharray: '2,4', strokeWidth: 1.5 },
  service: { stroke: '#8B5CF6', strokeDasharray: '8,3', strokeWidth: 1.5 },
  dotted_line: { stroke: '#6B7280', strokeDasharray: '2,2', strokeWidth: 1 },
};

// Calculate node positions based on layout type
function calculateNodePositions(
  nodes: DiagramNode[],
  layoutType: string,
  width: number,
  height: number
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const padding = 80;
  const nodeWidth = 120;
  const nodeHeight = 50;

  // If nodes have explicit positions, use them
  const hasExplicitPositions = nodes.some(n => n.x !== undefined && n.y !== undefined);
  if (hasExplicitPositions) {
    // Find bounds of explicit positions
    const xs = nodes.filter(n => n.x !== undefined).map(n => n.x!);
    const ys = nodes.filter(n => n.y !== undefined).map(n => n.y!);
    const minX = Math.min(...xs, 0);
    const maxX = Math.max(...xs, 1);
    const minY = Math.min(...ys, 0);
    const maxY = Math.max(...ys, 1);
    const scaleX = (width - padding * 2 - nodeWidth) / Math.max(maxX - minX, 1);
    const scaleY = (height - padding * 2 - nodeHeight) / Math.max(maxY - minY, 1);

    nodes.forEach(node => {
      if (node.x !== undefined && node.y !== undefined) {
        positions.set(node.id, {
          x: padding + (node.x - minX) * scaleX + nodeWidth / 2,
          y: padding + (node.y - minY) * scaleY + nodeHeight / 2,
        });
      }
    });

    // Position any nodes without explicit coords
    let idx = 0;
    nodes.filter(n => n.x === undefined || n.y === undefined).forEach(node => {
      positions.set(node.id, {
        x: padding + nodeWidth / 2 + (idx % 3) * (nodeWidth + 40),
        y: height - padding - nodeHeight / 2 - Math.floor(idx / 3) * (nodeHeight + 30),
      });
      idx++;
    });

    return positions;
  }

  // Group by level if available
  const byLevel = new Map<number, DiagramNode[]>();
  nodes.forEach(node => {
    const level = node.level ?? 0;
    if (!byLevel.has(level)) byLevel.set(level, []);
    byLevel.get(level)!.push(node);
  });
  const levels = Array.from(byLevel.keys()).sort((a, b) => a - b);

  switch (layoutType) {
    case 'hierarchical': {
      const levelHeight = (height - padding * 2) / Math.max(levels.length, 1);
      levels.forEach((level, levelIdx) => {
        const nodesAtLevel = byLevel.get(level)!;
        const levelWidth = width - padding * 2;
        const nodeSpacing = levelWidth / (nodesAtLevel.length + 1);
        nodesAtLevel.forEach((node, nodeIdx) => {
          positions.set(node.id, {
            x: padding + nodeSpacing * (nodeIdx + 1),
            y: padding + levelHeight * levelIdx + levelHeight / 2,
          });
        });
      });
      break;
    }

    case 'hub_spoke': {
      // First node or executive type at center
      const centerNode = nodes.find(n => n.type === 'executive') || nodes[0];
      const centerX = width / 2;
      const centerY = height / 2;
      positions.set(centerNode.id, { x: centerX, y: centerY });

      const otherNodes = nodes.filter(n => n.id !== centerNode.id);
      const radius = Math.min(width, height) / 2 - padding - 40;
      otherNodes.forEach((node, idx) => {
        const angle = (2 * Math.PI * idx) / otherNodes.length - Math.PI / 2;
        positions.set(node.id, {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        });
      });
      break;
    }

    case 'circular': {
      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(width, height) / 2 - padding - 40;
      nodes.forEach((node, idx) => {
        const angle = (2 * Math.PI * idx) / nodes.length - Math.PI / 2;
        positions.set(node.id, {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        });
      });
      break;
    }

    case 'matrix': {
      // Arrange in grid
      const cols = Math.ceil(Math.sqrt(nodes.length));
      const rows = Math.ceil(nodes.length / cols);
      const cellWidth = (width - padding * 2) / cols;
      const cellHeight = (height - padding * 2) / rows;
      nodes.forEach((node, idx) => {
        const col = idx % cols;
        const row = Math.floor(idx / cols);
        positions.set(node.id, {
          x: padding + cellWidth * col + cellWidth / 2,
          y: padding + cellHeight * row + cellHeight / 2,
        });
      });
      break;
    }

    case 'network':
    default: {
      // Force-directed-like layout (simplified)
      const cols = Math.ceil(Math.sqrt(nodes.length));
      const cellWidth = (width - padding * 2) / cols;
      const cellHeight = (height - padding * 2) / Math.ceil(nodes.length / cols);
      nodes.forEach((node, idx) => {
        const col = idx % cols;
        const row = Math.floor(idx / cols);
        // Add some randomness for network feel
        const jitterX = (Math.sin(idx * 7) * cellWidth * 0.15);
        const jitterY = (Math.cos(idx * 11) * cellHeight * 0.15);
        positions.set(node.id, {
          x: padding + cellWidth * col + cellWidth / 2 + jitterX,
          y: padding + cellHeight * row + cellHeight / 2 + jitterY,
        });
      });
      break;
    }
  }

  return positions;
}

export default function ArchetypeDiagram({ diagram, width = 600, height = 400 }: ArchetypeDiagramProps) {
  const positions = useMemo(
    () => calculateNodePositions(diagram.nodes, diagram.layout_type, width, height),
    [diagram.nodes, diagram.layout_type, width, height]
  );

  const nodeWidth = 120;
  const nodeHeight = 50;

  // Get connection path
  const getConnectionPath = (conn: DiagramConnection): string | null => {
    const from = positions.get(conn.from);
    const to = positions.get(conn.to);
    if (!from || !to) return null;

    // Curved line for better visibility
    const midX = (from.x + to.x) / 2;
    const midY = (from.y + to.y) / 2;
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    // Add slight curve
    const curvature = Math.min(dist * 0.15, 30);
    const perpX = -dy / dist * curvature;
    const perpY = dx / dist * curvature;

    return `M ${from.x} ${from.y} Q ${midX + perpX} ${midY + perpY} ${to.x} ${to.y}`;
  };

  // Get unique node types for legend
  const usedNodeTypes = [...new Set(diagram.nodes.map(n => n.type))];
  const usedConnectionTypes = [...new Set(diagram.connections.map(c => c.type))];
  const hasDifferentiatingNodes = diagram.nodes.some(n => n.is_differentiating);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h4 className="font-semibold text-gray-800 mb-2">{diagram.title}</h4>

      <svg width={width} height={height} className="bg-gray-50 rounded">
        <defs>
          {/* Arrow marker */}
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#374151" />
          </marker>
          <marker
            id="arrowhead-blue"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#3B82F6" />
          </marker>
        </defs>

        {/* Connections */}
        {diagram.connections.map((conn, idx) => {
          const path = getConnectionPath(conn);
          if (!path) return null;
          const style = CONNECTION_STYLES[conn.type] || CONNECTION_STYLES.reporting;
          return (
            <g key={`conn-${idx}`}>
              <path
                d={path}
                fill="none"
                stroke={style.stroke}
                strokeWidth={style.strokeWidth}
                strokeDasharray={style.strokeDasharray}
                markerEnd={conn.type === 'reporting' ? 'url(#arrowhead)' : undefined}
              />
              {conn.label && (
                <text
                  x={(positions.get(conn.from)!.x + positions.get(conn.to)!.x) / 2}
                  y={(positions.get(conn.from)!.y + positions.get(conn.to)!.y) / 2 - 5}
                  textAnchor="middle"
                  className="text-xs fill-gray-500"
                  fontSize={10}
                >
                  {conn.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {diagram.nodes.map((node) => {
          const pos = positions.get(node.id);
          if (!pos) return null;
          const colors = NODE_COLORS[node.type] || NODE_COLORS.department;
          const isDifferentiating = node.is_differentiating === true;

          return (
            <g key={node.id} className="cursor-pointer hover:opacity-90">
              {/* Glow effect for differentiating nodes */}
              {isDifferentiating && (
                <>
                  <rect
                    x={pos.x - nodeWidth / 2 - 4}
                    y={pos.y - nodeHeight / 2 - 4}
                    width={nodeWidth + 8}
                    height={nodeHeight + 8}
                    rx={10}
                    ry={10}
                    fill="none"
                    stroke="#F59E0B"
                    strokeWidth={3}
                    opacity={0.6}
                  />
                  <rect
                    x={pos.x - nodeWidth / 2 - 6}
                    y={pos.y - nodeHeight / 2 - 6}
                    width={nodeWidth + 12}
                    height={nodeHeight + 12}
                    rx={12}
                    ry={12}
                    fill="none"
                    stroke="#FCD34D"
                    strokeWidth={2}
                    opacity={0.3}
                  />
                </>
              )}
              <rect
                x={pos.x - nodeWidth / 2}
                y={pos.y - nodeHeight / 2}
                width={nodeWidth}
                height={nodeHeight}
                rx={8}
                ry={8}
                fill={colors.fill}
                stroke={isDifferentiating ? '#F59E0B' : colors.stroke}
                strokeWidth={isDifferentiating ? 3 : 2}
              />
              {/* Star icon for differentiating nodes */}
              {isDifferentiating && (
                <text
                  x={pos.x + nodeWidth / 2 - 12}
                  y={pos.y - nodeHeight / 2 + 12}
                  fontSize={14}
                  className="pointer-events-none"
                >
                  &#9733;
                </text>
              )}
              <text
                x={pos.x}
                y={pos.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={colors.text}
                fontSize={12}
                fontWeight="500"
                className="pointer-events-none"
              >
                {node.label.length > 14 ? node.label.substring(0, 12) + '...' : node.label}
              </text>
              <title>
                {node.label}
                {node.description ? `: ${node.description}` : ''}
                {isDifferentiating && node.differentiating_activity ? `\n\nDifferentiating Activity: ${node.differentiating_activity}` : ''}
              </title>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-4 text-xs">
        {/* Node types */}
        <div className="flex flex-wrap gap-2">
          <span className="text-gray-500 font-medium">Units:</span>
          {usedNodeTypes.map(type => (
            <span key={type} className="flex items-center gap-1">
              <span
                className="w-3 h-3 rounded"
                style={{ backgroundColor: NODE_COLORS[type]?.fill || '#6B7280' }}
              />
              <span className="capitalize">{type.replace('_', ' ')}</span>
            </span>
          ))}
        </div>

        {/* Connection types */}
        <div className="flex flex-wrap gap-2">
          <span className="text-gray-500 font-medium">Lines:</span>
          {usedConnectionTypes.map(type => {
            const style = CONNECTION_STYLES[type];
            return (
              <span key={type} className="flex items-center gap-1">
                <svg width={20} height={10}>
                  <line
                    x1={0}
                    y1={5}
                    x2={20}
                    y2={5}
                    stroke={style?.stroke || '#6B7280'}
                    strokeWidth={style?.strokeWidth || 1}
                    strokeDasharray={style?.strokeDasharray}
                  />
                </svg>
                <span className="capitalize">{type.replace('_', ' ')}</span>
              </span>
            );
          })}
        </div>

        {/* Differentiating indicator */}
        {hasDifferentiatingNodes && (
          <div className="flex items-center gap-1">
            <span className="text-gray-500 font-medium">Differentiating:</span>
            <span className="flex items-center gap-1">
              <span className="text-amber-500">&#9733;</span>
              <span
                className="w-3 h-3 rounded border-2"
                style={{ borderColor: '#F59E0B', backgroundColor: 'transparent' }}
              />
              <span className="text-amber-600 font-medium">Competitive Advantage</span>
            </span>
          </div>
        )}
      </div>

      {diagram.legend && (
        <p className="text-xs text-gray-500 mt-2 italic">{diagram.legend}</p>
      )}
    </div>
  );
}
