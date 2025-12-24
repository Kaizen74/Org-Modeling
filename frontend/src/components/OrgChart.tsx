import { useCallback, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  BackgroundVariant,
  NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { OrgNode, OrgEdge } from '../api/types'
import { User, MapPin, Briefcase } from 'lucide-react'

interface OrgChartProps {
  nodes: OrgNode[]
  edges: OrgEdge[]
  onNodeClick?: (node: OrgNode) => void
  onEdgeChange?: (source: string, target: string) => void
}

// Custom node component
function OrgNodeComponent({ data }: { data: OrgNode['data'] }) {
  const statusClasses = useMemo(() => {
    if (data.is_new) return 'border-green-500 bg-green-50'
    if (data.is_modified) return 'border-yellow-500 bg-yellow-50'
    if (data.is_vacant) return 'border-dashed border-slate-400 opacity-70'
    return 'border-slate-200 bg-white'
  }, [data])

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 shadow-sm min-w-[180px] ${statusClasses}`}
    >
      <div className="flex items-start gap-2">
        <div className="p-1.5 bg-blue-100 rounded-lg">
          <User className="h-4 w-4 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-slate-900 truncate">{data.label}</p>
          <p className="text-sm text-slate-600 truncate">{data.title}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
        {data.function && (
          <span className="flex items-center gap-1">
            <Briefcase className="h-3 w-3" />
            {data.function}
          </span>
        )}
        {data.location && (
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {data.location}
          </span>
        )}
      </div>

      {data.grade && (
        <div className="mt-2">
          <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">
            {data.grade}
          </span>
        </div>
      )}

      {(data.is_new || data.is_modified || data.is_vacant) && (
        <div className="mt-2 flex gap-1">
          {data.is_new && (
            <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">
              New
            </span>
          )}
          {data.is_modified && (
            <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded">
              Modified
            </span>
          )}
          {data.is_vacant && (
            <span className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">
              Vacant
            </span>
          )}
        </div>
      )}
    </div>
  )
}

const nodeTypes: NodeTypes = {
  custom: OrgNodeComponent,
}

export default function OrgChart({
  nodes: initialNodes,
  edges: initialEdges,
  onNodeClick,
  onEdgeChange,
}: OrgChartProps) {
  // Transform nodes to React Flow format
  const flowNodes = useMemo(() => {
    return initialNodes.map((node) => ({
      id: node.id,
      type: 'custom',
      position: node.position,
      data: node.data,
    }))
  }, [initialNodes])

  const flowEdges = useMemo(() => {
    return initialEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      animated: false,
      style: { stroke: '#94a3b8', strokeWidth: 2 },
    }))
  }, [initialEdges])

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)

  // Sync nodes when initialNodes changes (e.g., after API call)
  useEffect(() => {
    setNodes(flowNodes)
  }, [flowNodes, setNodes])

  // Sync edges when initialEdges changes (e.g., after API call)
  useEffect(() => {
    setEdges(flowEdges)
  }, [flowEdges, setEdges])

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge(params, eds))
      if (onEdgeChange && params.source && params.target) {
        onEdgeChange(params.source, params.target)
      }
    },
    [setEdges, onEdgeChange]
  )

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        const orgNode = initialNodes.find((n) => n.id === node.id)
        if (orgNode) onNodeClick(orgNode)
      }
    },
    [initialNodes, onNodeClick]
  )

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
      >
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as OrgNode['data']
            if (data.is_new) return '#22c55e'
            if (data.is_modified) return '#f59e0b'
            if (data.is_vacant) return '#94a3b8'
            return '#3b82f6'
          }}
          maskColor="rgb(248, 250, 252, 0.8)"
        />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
      </ReactFlow>
    </div>
  )
}
