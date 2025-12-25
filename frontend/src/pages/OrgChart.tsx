import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Loader2, AlertTriangle, ArrowRight } from 'lucide-react';
import { orgDataApi } from '../services/api';
import type { Employee } from '../types';

interface HierarchyNode {
  name: string;
  data: Employee;
  children: HierarchyNode[];
}

const GRADE_COLORS: Record<string, string> = {
  'SVP': '#1e40af',
  'H8': '#1d4ed8',
  'H7': '#2563eb',
  'H6': '#3b82f6',
  'H5': '#60a5fa',
  'TL': '#10b981',
  'AO': '#6b7280',
};

const LEVEL_Y_OFFSET = 150;
const NODE_X_SPACING = 200;

export default function OrgChart() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Employee | null>(null);

  useEffect(() => {
    fetchOrgData();
  }, []);

  const fetchOrgData = async () => {
    try {
      const data = await orgDataApi.getLatest();
      if (data.hierarchy && Object.keys(data.hierarchy).length > 0) {
        const { nodes: flowNodes, edges: flowEdges } = convertHierarchyToFlow(
          data.hierarchy as HierarchyNode
        );
        setNodes(flowNodes);
        setEdges(flowEdges);
      } else {
        setError('No hierarchy data available');
      }
    } catch (err) {
      setError('No org data available. Please upload a CSV first.');
    } finally {
      setLoading(false);
    }
  };

  const convertHierarchyToFlow = (hierarchy: HierarchyNode) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Calculate tree layout
    const nodePositions = new Map<string, { x: number; y: number }>();

    // First pass: count nodes at each level for positioning
    const levelWidths: number[] = [];
    const countNodesAtLevel = (node: HierarchyNode, level: number) => {
      if (!levelWidths[level]) levelWidths[level] = 0;
      levelWidths[level]++;
      node.children?.forEach(child => countNodesAtLevel(child, level + 1));
    };
    countNodesAtLevel(hierarchy, 0);

    // Second pass: position nodes
    const levelCounters: number[] = new Array(levelWidths.length).fill(0);

    const processNode = (node: HierarchyNode, level: number, parentId?: string) => {
      const nodeId = node.name;

      // Calculate x position based on level width
      const levelWidth = levelWidths[level] * NODE_X_SPACING;
      const startX = -levelWidth / 2;
      const x = startX + (levelCounters[level] * NODE_X_SPACING) + NODE_X_SPACING / 2;
      const y = level * LEVEL_Y_OFFSET;

      levelCounters[level]++;
      nodePositions.set(nodeId, { x, y });

      const grade = node.data?.grade || 'AO';
      const bgColor = GRADE_COLORS[grade] || '#6b7280';

      nodes.push({
        id: nodeId,
        type: 'default',
        position: { x, y },
        data: {
          label: (
            <div className="text-center">
              <div className="font-semibold text-xs">{node.name}</div>
              <div className="text-xs opacity-80">{node.data?.job_title || ''}</div>
              <div className="text-xs opacity-60">{grade}</div>
            </div>
          ),
        },
        style: {
          background: bgColor,
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '11px',
          width: 'auto',
          minWidth: '120px',
        },
      });

      if (parentId) {
        edges.push({
          id: `${parentId}-${nodeId}`,
          source: parentId,
          target: nodeId,
          type: 'smoothstep',
          style: { stroke: '#94a3b8' },
        });
      }

      node.children?.forEach(child => processNode(child, level + 1, nodeId));
    };

    processNode(hierarchy, 0);

    return { nodes, edges };
  };

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    // Find employee data from the original hierarchy
    // For now, just show the node ID
    setSelectedNode({ name: node.id } as Employee);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Org Chart</h1>
        <div className="card text-center py-8">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-gray-600 mb-2">No Org Data Available</h2>
          <p className="text-gray-500 mb-4">{error}</p>
          <Link to="/upload" className="btn btn-primary inline-flex items-center gap-2">
            Upload CSV <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Org Chart</h1>
        <div className="flex items-center gap-4">
          {/* Legend */}
          <div className="flex items-center gap-2 text-xs">
            {Object.entries(GRADE_COLORS).map(([grade, color]) => (
              <div key={grade} className="flex items-center gap-1">
                <div
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: color }}
                />
                <span>{grade}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card p-0" style={{ height: '600px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Controls />
          <Background color="#e5e7eb" gap={16} />
        </ReactFlow>
      </div>

      {/* Node Details Panel */}
      {selectedNode && (
        <div className="mt-4 card">
          <h3 className="font-semibold mb-2">Selected: {selectedNode.name}</h3>
          {selectedNode.job_title && (
            <p className="text-sm text-gray-600">Title: {selectedNode.job_title}</p>
          )}
          {selectedNode.department && (
            <p className="text-sm text-gray-600">Department: {selectedNode.department}</p>
          )}
        </div>
      )}
    </div>
  );
}
