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

// Calculate dynamic node dimensions based on labels
function calculateNodeDimensions(nodes: DiagramNode[]): { width: number; height: number } {
  const maxLabelLength = Math.max(...nodes.map(n => n.label.length), 10);
  // Base width on label length, with min 100 and max 180
  const width = Math.min(180, Math.max(100, maxLabelLength * 8 + 20));
  const height = 45;
  return { width, height };
}

// Calculate required diagram dimensions based on nodes
function calculateDiagramDimensions(
  nodes: DiagramNode[],
  layoutType: string,
  nodeWidth: number,
  nodeHeight: number
): { width: number; height: number } {
  // Group by level to understand structure
  const byLevel = new Map<number, DiagramNode[]>();
  nodes.forEach(node => {
    const level = node.level ?? 0;
    if (!byLevel.has(level)) byLevel.set(level, []);
    byLevel.get(level)!.push(node);
  });

  const levels = Array.from(byLevel.keys()).sort((a, b) => a - b);
  const maxNodesAtLevel = Math.max(...Array.from(byLevel.values()).map(arr => arr.length), 1);

  // Calculate minimum required dimensions
  const horizontalGap = 30; // Gap between nodes horizontally
  const verticalGap = 80; // Gap between levels vertically
  const padding = 60;

  let minWidth: number;
  let minHeight: number;

  if (layoutType === 'hierarchical') {
    minWidth = maxNodesAtLevel * (nodeWidth + horizontalGap) + padding * 2;
    minHeight = levels.length * (nodeHeight + verticalGap) + padding * 2;
  } else if (layoutType === 'hub_spoke' || layoutType === 'circular') {
    const radius = Math.max(nodes.length * 25, 120);
    minWidth = radius * 2 + nodeWidth + padding * 2;
    minHeight = radius * 2 + nodeHeight + padding * 2;
  } else {
    // Matrix or network
    const cols = Math.ceil(Math.sqrt(nodes.length));
    const rows = Math.ceil(nodes.length / cols);
    minWidth = cols * (nodeWidth + horizontalGap) + padding * 2;
    minHeight = rows * (nodeHeight + verticalGap) + padding * 2;
  }

  return {
    width: Math.max(minWidth, 700),
    height: Math.max(minHeight, 450)
  };
}

// Calculate node positions based on layout type
function calculateNodePositions(
  nodes: DiagramNode[],
  layoutType: string,
  width: number,
  height: number,
  nodeWidth: number,
  nodeHeight: number
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const padding = 60;
  const horizontalGap = 30;
  const verticalGap = 80;

  // If nodes have explicit positions, use them with better scaling
  const hasExplicitPositions = nodes.some(n => n.x !== undefined && n.y !== undefined);
  if (hasExplicitPositions) {
    const xs = nodes.filter(n => n.x !== undefined).map(n => n.x!);
    const ys = nodes.filter(n => n.y !== undefined).map(n => n.y!);
    const minX = Math.min(...xs, 0);
    const maxX = Math.max(...xs, 1);
    const minY = Math.min(...ys, 0);
    const maxY = Math.max(...ys, 1);

    const availableWidth = width - padding * 2 - nodeWidth;
    const availableHeight = height - padding * 2 - nodeHeight;
    const scaleX = availableWidth / Math.max(maxX - minX, 1);
    const scaleY = availableHeight / Math.max(maxY - minY, 1);

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
        x: padding + nodeWidth / 2 + (idx % 3) * (nodeWidth + horizontalGap),
        y: height - padding - nodeHeight / 2 - Math.floor(idx / 3) * (nodeHeight + verticalGap),
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
      const availableHeight = height - padding * 2;
      const levelHeight = availableHeight / Math.max(levels.length, 1);

      levels.forEach((level, levelIdx) => {
        const nodesAtLevel = byLevel.get(level)!;
        const totalNodesWidth = nodesAtLevel.length * nodeWidth + (nodesAtLevel.length - 1) * horizontalGap;
        const startX = (width - totalNodesWidth) / 2;

        nodesAtLevel.forEach((node, nodeIdx) => {
          positions.set(node.id, {
            x: startX + nodeIdx * (nodeWidth + horizontalGap) + nodeWidth / 2,
            y: padding + levelHeight * levelIdx + levelHeight / 2,
          });
        });
      });
      break;
    }

    case 'hub_spoke': {
      const centerNode = nodes.find(n => n.type === 'executive') || nodes[0];
      const centerX = width / 2;
      const centerY = height / 2;
      positions.set(centerNode.id, { x: centerX, y: centerY });

      const otherNodes = nodes.filter(n => n.id !== centerNode.id);
      const radius = Math.min(
        (width - padding * 2 - nodeWidth) / 2,
        (height - padding * 2 - nodeHeight) / 2
      ) * 0.85;

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
      const radius = Math.min(
        (width - padding * 2 - nodeWidth) / 2,
        (height - padding * 2 - nodeHeight) / 2
      ) * 0.85;

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
      const cols = Math.ceil(Math.sqrt(nodes.length));
      const rows = Math.ceil(nodes.length / cols);
      const totalWidth = cols * nodeWidth + (cols - 1) * horizontalGap;
      const totalHeight = rows * nodeHeight + (rows - 1) * verticalGap;
      const startX = (width - totalWidth) / 2;
      const startY = (height - totalHeight) / 2;

      nodes.forEach((node, idx) => {
        const col = idx % cols;
        const row = Math.floor(idx / cols);
        positions.set(node.id, {
          x: startX + col * (nodeWidth + horizontalGap) + nodeWidth / 2,
          y: startY + row * (nodeHeight + verticalGap) + nodeHeight / 2,
        });
      });
      break;
    }

    case 'network':
    default: {
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
  }

  return positions;
}

// Truncate label with ellipsis, allowing more characters for wider nodes
function truncateLabel(label: string, nodeWidth: number): string {
  const maxChars = Math.floor((nodeWidth - 20) / 7); // Approximate char width
  if (label.length <= maxChars) return label;
  return label.substring(0, maxChars - 2) + '...';
}

export default function ArchetypeDiagram({ diagram, width: propWidth, height: propHeight }: ArchetypeDiagramProps) {
  // Calculate dynamic dimensions
  const nodeDimensions = useMemo(
    () => calculateNodeDimensions(diagram.nodes),
    [diagram.nodes]
  );

  const nodeWidth = nodeDimensions.width;
  const nodeHeight = nodeDimensions.height;

  // Auto-calculate diagram size if not provided
  const calculatedDimensions = useMemo(
    () => calculateDiagramDimensions(diagram.nodes, diagram.layout_type, nodeWidth, nodeHeight),
    [diagram.nodes, diagram.layout_type, nodeWidth, nodeHeight]
  );

  const width = propWidth || calculatedDimensions.width;
  const height = propHeight || calculatedDimensions.height;

  const positions = useMemo(
    () => calculateNodePositions(diagram.nodes, diagram.layout_type, width, height, nodeWidth, nodeHeight),
    [diagram.nodes, diagram.layout_type, width, height, nodeWidth, nodeHeight]
  );

  // Get connection path - simplified to avoid label overlap
  const getConnectionPath = (conn: DiagramConnection): { path: string; labelPos: { x: number; y: number } } | null => {
    const from = positions.get(conn.from);
    const to = positions.get(conn.to);
    if (!from || !to) return null;

    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    // Simple curved line
    const midX = (from.x + to.x) / 2;
    const midY = (from.y + to.y) / 2;

    // Add curve perpendicular to the line
    const curvature = Math.min(dist * 0.1, 20);
    const perpX = -dy / dist * curvature;
    const perpY = dx / dist * curvature;

    const path = `M ${from.x} ${from.y} Q ${midX + perpX} ${midY + perpY} ${to.x} ${to.y}`;

    // Position label offset from the line
    const labelPos = {
      x: midX + perpX * 2,
      y: midY + perpY * 2 - 8
    };

    return { path, labelPos };
  };

  // Get unique node types for legend
  const usedNodeTypes = [...new Set(diagram.nodes.map(n => n.type))];
  const usedConnectionTypes = [...new Set(diagram.connections.map(c => c.type))];
  const hasDifferentiatingNodes = diagram.nodes.some(n => n.is_differentiating);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 overflow-x-auto">
      <h4 className="font-semibold text-gray-800 mb-2">{diagram.title}</h4>

      <svg
        width={width}
        height={height}
        className="bg-gray-50 rounded"
        style={{ minWidth: width, minHeight: height }}
      >
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

        {/* Connections - rendered first so they appear behind nodes */}
        {diagram.connections.map((conn, idx) => {
          const pathData = getConnectionPath(conn);
          if (!pathData) return null;
          const style = CONNECTION_STYLES[conn.type] || CONNECTION_STYLES.reporting;
          return (
            <g key={`conn-${idx}`}>
              <path
                d={pathData.path}
                fill="none"
                stroke={style.stroke}
                strokeWidth={style.strokeWidth}
                strokeDasharray={style.strokeDasharray}
                markerEnd={conn.type === 'reporting' ? 'url(#arrowhead)' : undefined}
              />
              {/* Only show short connection labels */}
              {conn.label && conn.label.length <= 15 && (
                <g>
                  {/* Background for readability */}
                  <rect
                    x={pathData.labelPos.x - conn.label.length * 3}
                    y={pathData.labelPos.y - 8}
                    width={conn.label.length * 6}
                    height={12}
                    fill="white"
                    fillOpacity={0.8}
                    rx={2}
                  />
                  <text
                    x={pathData.labelPos.x}
                    y={pathData.labelPos.y}
                    textAnchor="middle"
                    fill="#6B7280"
                    fontSize={9}
                  >
                    {conn.label}
                  </text>
                </g>
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
                    x={pos.x - nodeWidth / 2 - 5}
                    y={pos.y - nodeHeight / 2 - 5}
                    width={nodeWidth + 10}
                    height={nodeHeight + 10}
                    rx={10}
                    ry={10}
                    fill="none"
                    stroke="#F59E0B"
                    strokeWidth={3}
                    opacity={0.7}
                  />
                </>
              )}
              <rect
                x={pos.x - nodeWidth / 2}
                y={pos.y - nodeHeight / 2}
                width={nodeWidth}
                height={nodeHeight}
                rx={6}
                ry={6}
                fill={colors.fill}
                stroke={isDifferentiating ? '#F59E0B' : colors.stroke}
                strokeWidth={isDifferentiating ? 3 : 2}
              />
              {/* Star icon for differentiating nodes - positioned outside */}
              {isDifferentiating && (
                <text
                  x={pos.x + nodeWidth / 2 - 2}
                  y={pos.y - nodeHeight / 2 - 2}
                  fontSize={16}
                  fill="#F59E0B"
                  className="pointer-events-none"
                >
                  ★
                </text>
              )}
              {/* Node label */}
              <text
                x={pos.x}
                y={pos.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={colors.text}
                fontSize={11}
                fontWeight="500"
                className="pointer-events-none"
              >
                {truncateLabel(node.label, nodeWidth)}
              </text>
              <title>
                {node.label}
                {node.description ? `\n${node.description}` : ''}
                {isDifferentiating && node.differentiating_activity ? `\n\n★ Differentiating: ${node.differentiating_activity}` : ''}
              </title>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-4 text-xs">
        {/* Node types */}
        <div className="flex flex-wrap gap-2 items-center">
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
        <div className="flex flex-wrap gap-2 items-center">
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
              <span className="text-amber-500 text-sm">★</span>
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
