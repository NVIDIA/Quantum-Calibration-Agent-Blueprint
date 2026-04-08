/*
 * SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use client';

import { useCallback, useMemo, useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  NodeProps,
} from 'reactflow';
import dagre from 'dagre';
import dynamic from 'next/dynamic';
import 'reactflow/dist/style.css';
import { useTheme } from '@/contexts/ThemeContext';
import { HTTP_PROXY_PATH } from '@/constants';

// Dynamic import for Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface WorkflowNode {
  id: string;
  name: string;
  state: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  run_count: number;
  extracted?: Record<string, any>;
  dependencies?: string[];
  experiment_id?: string;
}

interface WorkflowGraphProps {
  nodes: WorkflowNode[];
}

// Color scheme for node states - light and dark mode
const NODE_COLORS = {
  light: {
    success: { bg: '#dcfce7', border: '#22c55e', text: '#166534' },
    failed: { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' },
    running: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
    pending: { bg: '#f3f4f6', border: '#9ca3af', text: '#374151' },
    skipped: { bg: '#f3f4f6', border: '#d1d5db', text: '#6b7280' },
  },
  dark: {
    success: { bg: '#166534', border: '#22c55e', text: '#dcfce7' },
    failed: { bg: '#7f1d1d', border: '#ef4444', text: '#fecaca' },
    running: { bg: '#1e3a5f', border: '#3b82f6', text: '#bfdbfe' },
    pending: { bg: '#374151', border: '#6b7280', text: '#d1d5db' },
    skipped: { bg: '#374151', border: '#4b5563', text: '#9ca3af' },
  },
};

// Custom node component with hover tooltip
const CustomNode = ({ data, selected }: NodeProps) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [plotData, setPlotData] = useState<any>(null);
  const [plotLoading, setPlotLoading] = useState(false);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const nodeRef = useRef<HTMLDivElement>(null);
  const isDark = data.isDark || false;
  const colorScheme = isDark ? NODE_COLORS.dark : NODE_COLORS.light;
  const colors = colorScheme[data.state as keyof typeof colorScheme] || colorScheme.pending;

  // Fetch plot when tooltip is shown and experiment_id exists
  useEffect(() => {
    if (showTooltip && data.experiment_id && !plotData && !plotLoading) {
      setPlotLoading(true);
      // First get list of plots
      fetch(`${HTTP_PROXY_PATH}/history/${data.experiment_id}/plots`)
        .then(res => res.json())
        .then(plotList => {
          if (plotList.plots && plotList.plots.length > 0) {
            // Fetch first plot
            const firstPlot = plotList.plots[0];
            return fetch(`${HTTP_PROXY_PATH}/history/${data.experiment_id}/plot/${encodeURIComponent(firstPlot.name)}`);
          }
          return null;
        })
        .then(res => res?.json())
        .then(plot => {
          if (plot && plot.data) {
            setPlotData(plot.data);
          }
          setPlotLoading(false);
        })
        .catch(() => {
          setPlotLoading(false);
        });
    }
  }, [showTooltip, data.experiment_id, plotData, plotLoading]);

  // Clear plot data when tooltip hides
  useEffect(() => {
    if (!showTooltip) {
      setPlotData(null);
    }
  }, [showTooltip]);

  const handleMouseEnter = useCallback(() => {
    setShowTooltip(true);
    if (nodeRef.current) {
      const rect = nodeRef.current.getBoundingClientRect();
      setTooltipPos({ x: rect.right + 8, y: rect.top + rect.height / 2 });
    }
  }, []);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
  }, []);

  // Theme-aware colors for portal tooltip (dark: classes don't work outside React tree)
  const tt = isDark
    ? { bg: '#1f2937', border: '#374151', text: '#e5e7eb', textDim: '#9ca3af', textMid: '#d1d5db', divider: '#4b5563', noPlot: '#6b7280', arrow: '#1f2937' }
    : { bg: '#ffffff', border: '#e5e7eb', text: '#1f2937', textDim: '#6b7280', textMid: '#374151', divider: '#e5e7eb', noPlot: '#9ca3af', arrow: '#ffffff' };

  const tooltip = showTooltip && tooltipPos ? createPortal(
    <div
      className={plotData ? 'w-96' : 'w-64'}
      style={{
        position: 'fixed',
        left: tooltipPos.x,
        top: tooltipPos.y,
        transform: 'translateY(-50%)',
        zIndex: 10000,
        pointerEvents: 'none',
        padding: 12,
        backgroundColor: tt.bg,
        borderRadius: 8,
        boxShadow: '0 20px 25px -5px rgba(0,0,0,.1), 0 8px 10px -6px rgba(0,0,0,.1)',
        border: `1px solid ${tt.border}`,
      }}
    >
      <div className="text-sm font-semibold mb-2" style={{ color: tt.text }}>
        {data.name}
      </div>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span style={{ color: tt.textDim }}>ID:</span>
          <span className="font-mono" style={{ color: tt.textMid }}>{data.id}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: tt.textDim }}>State:</span>
          <span className="font-medium capitalize" style={{ color: colors.border }}>
            {data.state}
          </span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: tt.textDim }}>Run Count:</span>
          <span style={{ color: tt.textMid }}>{data.run_count}</span>
        </div>
        {data.extracted && Object.keys(data.extracted).length > 0 && (
          <div className="mt-2 pt-2" style={{ borderTop: `1px solid ${tt.divider}` }}>
            <div className="mb-1" style={{ color: tt.textDim }}>Extracted Values:</div>
            {Object.entries(data.extracted).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span style={{ color: tt.textDim }}>{key}:</span>
                <span className="font-mono" style={{ color: tt.text }}>
                  {typeof value === 'number' ? value.toFixed(4) : String(value)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Plot section */}
      {data.experiment_id && (
        <div className="mt-2 pt-2" style={{ borderTop: `1px solid ${tt.divider}` }}>
          {plotLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500"></div>
            </div>
          ) : plotData ? (
            <div className="h-48 w-full">
              <Plot
                data={plotData.data || []}
                layout={{
                  ...(plotData.layout || {}),
                  autosize: true,
                  margin: { l: 40, r: 20, t: 30, b: 40 },
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'transparent',
                  font: { color: isDark ? '#e5e7eb' : '#374151', size: 9 },
                  xaxis: { ...(plotData.layout?.xaxis || {}), gridcolor: isDark ? '#4b5563' : '#e5e7eb' },
                  yaxis: { ...(plotData.layout?.yaxis || {}), gridcolor: isDark ? '#4b5563' : '#e5e7eb' },
                }}
                config={{ displayModeBar: false, staticPlot: true }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            </div>
          ) : (
            <div className="text-xs text-center py-2" style={{ color: tt.noPlot }}>
              No plot available
            </div>
          )}
        </div>
      )}

      {/* Tooltip arrow - points left */}
      <div
        className="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0"
        style={{
          borderTop: '8px solid transparent',
          borderBottom: '8px solid transparent',
          borderRight: `8px solid ${tt.arrow}`,
        }}
      />
    </div>,
    document.body
  ) : null;

  return (
    <div
      ref={nodeRef}
      className="relative"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />

      <div
        className={`px-4 py-3 rounded-lg shadow-md transition-all duration-200 ${
          selected ? 'ring-2 ring-purple-500' : ''
        } ${data.state === 'running' ? 'animate-pulse' : ''}`}
        style={{
          backgroundColor: colors.bg,
          borderWidth: 2,
          borderColor: colors.border,
          borderStyle: 'solid',
          minWidth: 140,
        }}
      >
        <div
          className="text-sm font-medium text-center truncate"
          style={{ color: colors.text, maxWidth: 120 }}
        >
          {data.label}
        </div>
        <div
          className="text-xs text-center mt-1 capitalize"
          style={{ color: colors.text, opacity: 0.7 }}
        >
          {data.state}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />

      {tooltip}
    </div>
  );
};

const nodeTypes = { custom: CustomNode };

// Dagre layout helper
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });

  const nodeWidth = 160;
  const nodeHeight = 60;

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export const WorkflowGraph = ({ nodes: workflowNodes }: WorkflowGraphProps) => {
  const { lightMode } = useTheme();
  const isDark = lightMode === 'dark';

  // Convert workflow nodes to ReactFlow format
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    const rfNodes: Node[] = workflowNodes.map((node) => ({
      id: node.id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: {
        label: (node.name || node.id || '').length > 16 ? (node.name || node.id || '').slice(0, 14) + '...' : (node.name || node.id || ''),
        name: node.name || node.id || '',
        id: node.id,
        state: node.state,
        run_count: node.run_count,
        extracted: node.extracted,
        experiment_id: node.experiment_id,
        isDark,
      },
    }));

    const rfEdges: Edge[] = [];
    workflowNodes.forEach((node) => {
      (node.dependencies || []).forEach((depId) => {
        rfEdges.push({
          id: `${depId}-${node.id}`,
          source: depId,
          target: node.id,
          type: 'smoothstep',
          animated: node.state === 'running',
          style: { strokeWidth: 2, stroke: '#9ca3af' },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#9ca3af',
          },
        });
      });
    });

    // Apply dagre layout
    return getLayoutedElements(rfNodes, rfEdges);
  }, [workflowNodes, isDark]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Update nodes/edges when workflow data changes
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 0.75 }}
        minZoom={0.3}
        maxZoom={1.5}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color={isDark ? '#4b5563' : '#e5e7eb'} gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
};

export default WorkflowGraph;
