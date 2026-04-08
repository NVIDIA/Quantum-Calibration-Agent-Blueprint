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

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import {
  IconRefresh,
  IconCheck,
  IconX,
  IconPlayerPlay,
  IconPlayerStop,
  IconClock,
  IconChevronRight,
  IconChevronDown,
  IconChevronUp,
  IconListCheck,
  IconFileText,
  IconLayoutList,
  IconLoader,
  IconGitBranch,
  IconTool,
  IconFlask,
  IconAlertCircle,
  IconInfoCircle,
  IconTrash,
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import { HTTP_PROXY_PATH, WORKFLOWS_LIST, WORKFLOWS_DETAIL } from '@/constants';

// Dynamic imports for client-only components
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });
const WorkflowGraph = dynamic(() => import('./WorkflowGraph'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
    </div>
  ),
});

interface WorkflowNode {
  id: string;
  name: string;
  state: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  run_count: number;
  extracted?: Record<string, any>;
  dependencies?: string[];
  experiment_id?: string;
}

interface HistoryEvent {
  ts: string;
  event: string;
  node?: string;
  [key: string]: any;
}

interface WorkflowSummary {
  workflow_id: string;
  name: string;
  status: string;
  progress: string;
  completed: number;
  failed: number;
  running: number;
  total: number;
  current_node?: string;
  process_running?: boolean;
}

interface WorkflowDetail {
  workflow_id: string;
  name: string;
  objective?: string;
  status: string;
  process_running?: boolean;
  started_at?: string;
  completed_at?: string;
  context?: Record<string, any>;
  progress: {
    completed: number;
    failed: number;
    skipped: number;
    running: number;
    pending: number;
    total: number;
  };
  current_node?: {
    id: string;
    name: string;
    state: string;
    run_count: number;
  };
  nodes: WorkflowNode[];
  recent_history?: HistoryEvent[];
}

type TabType = 'graph' | 'nodes' | 'plan';

const STATUS_COLORS: Record<string, string> = {
  created: 'bg-gray-500',
  executing: 'bg-blue-500',
  stalled: 'bg-yellow-500',
  paused: 'bg-yellow-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

// Derive display status from workflow status and process_running
const getDisplayStatus = (status: string, processRunning?: boolean): string => {
  if (processRunning) {
    return 'executing';  // Process alive = always executing
  }
  if (status === 'running') {
    return 'stalled';    // Status says running but process dead
  }
  return status;         // created, completed, failed, paused
};

const NODE_ICONS: Record<string, React.ReactNode> = {
  success: <IconCheck className="w-4 h-4 text-green-500" />,
  failed: <IconX className="w-4 h-4 text-red-500" />,
  running: <IconPlayerPlay className="w-4 h-4 text-blue-500 animate-pulse" />,
  pending: <IconClock className="w-4 h-4 text-gray-400" />,
  skipped: <IconChevronRight className="w-4 h-4 text-gray-400" />,
};

const DEFAULT_PANEL_HEIGHT = 200;
const MIN_PANEL_HEIGHT = 100;
const MAX_PANEL_HEIGHT = 400;

// Log parsing types and functions
interface ParsedLogEntry {
  timestamp: string;
  type: 'tool_call' | 'tool_complete' | 'tool_error' | 'info';
  toolName?: string;
  duration?: string;
  details?: string;
  raw: string;
}

const parseLogLines = (logContent: string): ParsedLogEntry[] => {
  const lines = logContent.split('\n');
  const entries: ParsedLogEntry[] = [];
  let currentEntry: ParsedLogEntry | null = null;

  for (const line of lines) {
    if (!line.trim()) continue;

    // Match main log line: [TIMESTAMP] EMOJI Action
    const mainMatch = line.match(/^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*(.+)$/);

    if (mainMatch) {
      // Save previous entry
      if (currentEntry) {
        entries.push(currentEntry);
      }

      const [, timestamp, content] = mainMatch;

      // Detect type based on emoji/content
      if (content.includes('🔧 Calling tool:')) {
        const toolMatch = content.match(/🔧 Calling tool:\s*(\w+)/);
        currentEntry = {
          timestamp,
          type: 'tool_call',
          toolName: toolMatch?.[1],
          raw: line,
        };
      } else if (content.includes('✔') && content.includes('completed')) {
        const completeMatch = content.match(/✔\s*(\w+)\s+completed\s*\(([^)]+)\):\s*(.+)?/);
        currentEntry = {
          timestamp,
          type: 'tool_complete',
          toolName: completeMatch?.[1],
          duration: completeMatch?.[2],
          details: completeMatch?.[3],
          raw: line,
        };
      } else if (content.includes('✘') || content.includes('❌') || content.toLowerCase().includes('error')) {
        currentEntry = {
          timestamp,
          type: 'tool_error',
          details: content,
          raw: line,
        };
      } else {
        currentEntry = {
          timestamp,
          type: 'info',
          details: content,
          raw: line,
        };
      }
    } else if (line.match(/^\s+→\s*/) && currentEntry) {
      // Continuation line with arrow - append to current entry details
      const detailContent = line.replace(/^\s+→\s*/, '');
      currentEntry.details = currentEntry.details
        ? `${currentEntry.details}\n${detailContent}`
        : detailContent;
    } else if (currentEntry) {
      // Other continuation line
      currentEntry.details = currentEntry.details
        ? `${currentEntry.details}\n${line.trim()}`
        : line.trim();
    }
  }

  // Don't forget the last entry
  if (currentEntry) {
    entries.push(currentEntry);
  }

  return entries;
};

const LogEntryDisplay = ({ entry }: { entry: ParsedLogEntry }) => {
  const [expanded, setExpanded] = useState(false);

  const getTypeConfig = () => {
    switch (entry.type) {
      case 'tool_call':
        return {
          icon: <IconTool className="w-3.5 h-3.5" />,
          color: 'text-yellow-500',
        };
      case 'tool_complete':
        return {
          icon: <IconCheck className="w-3.5 h-3.5" />,
          color: 'text-green-500',
        };
      case 'tool_error':
        return {
          icon: <IconAlertCircle className="w-3.5 h-3.5" />,
          color: 'text-red-500',
        };
      default:
        return {
          icon: <IconInfoCircle className="w-3.5 h-3.5" />,
          color: 'text-blue-500',
        };
    }
  };

  const config = getTypeConfig();
  const hasDetails = entry.details && entry.details.length > 0;
  const timeOnly = entry.timestamp.split(' ')[1] || entry.timestamp;

  // Format display text
  let displayText = entry.toolName || 'Event';
  if (entry.type === 'tool_call') {
    displayText = `Calling ${entry.toolName}`;
  } else if (entry.type === 'tool_complete') {
    displayText = `${entry.toolName} completed`;
  }

  return (
    <div className="flex items-start gap-2 py-0.5">
      <span className="text-gray-500 dark:text-gray-500 whitespace-nowrap w-16 flex-shrink-0 font-mono text-xs">
        {timeOnly}
      </span>
      <span className={`flex-shrink-0 mt-0.5 ${config.color}`}>
        {config.icon}
      </span>
      <div className="flex-1 min-w-0">
        <div
          className={`flex items-center gap-1 ${hasDetails ? 'cursor-pointer' : ''}`}
          onClick={() => hasDetails && setExpanded(!expanded)}
        >
          <span className="text-gray-700 dark:text-gray-300 text-xs">
            {displayText}
          </span>
          {entry.duration && (
            <span className="text-gray-400 dark:text-gray-500 text-[10px]">
              ({entry.duration})
            </span>
          )}
          {hasDetails && (
            <span className="text-gray-400 dark:text-gray-600">
              {expanded ? (
                <IconChevronDown className="w-3 h-3" />
              ) : (
                <IconChevronRight className="w-3 h-3" />
              )}
            </span>
          )}
        </div>
        {expanded && hasDetails && (
          <div className="mt-1 text-[10px] text-gray-500 dark:text-gray-400 font-mono whitespace-pre-wrap break-all bg-gray-100 dark:bg-gray-800 rounded p-2">
            {entry.details}
          </div>
        )}
      </div>
    </div>
  );
};

// Plot display for a workflow node's experiment result
const NodePlot = ({ experimentId }: { experimentId: string }) => {
  const [plotData, setPlotData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${HTTP_PROXY_PATH}/history/${experimentId}/plots`)
      .then(res => res.json())
      .then(plotList => {
        if (cancelled) return;
        if (plotList.plots && plotList.plots.length > 0) {
          return fetch(`${HTTP_PROXY_PATH}/history/${experimentId}/plot/${encodeURIComponent(plotList.plots[0].name)}`);
        }
        return null;
      })
      .then(res => res?.json())
      .then(plot => {
        if (cancelled) return;
        if (plot && plot.data) {
          setPlotData(plot.data);
        }
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [experimentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 w-64">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!plotData) {
    return (
      <div className="flex items-center justify-center h-40 w-64 text-xs text-gray-400 dark:text-gray-500">
        No plot available
      </div>
    );
  }

  return (
    <div className="h-48 w-72">
      <Plot
        data={plotData.data || []}
        layout={{
          ...(plotData.layout || {}),
          autosize: true,
          margin: { l: 40, r: 10, t: 25, b: 35 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { size: 9 },
          xaxis: { ...(plotData.layout?.xaxis || {}), gridcolor: '#e5e7eb' },
          yaxis: { ...(plotData.layout?.yaxis || {}), gridcolor: '#e5e7eb' },
        }}
        config={{ displayModeBar: false, staticPlot: true }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  );
};

export const Workflows = () => {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [workflowDetail, setWorkflowDetail] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('graph');
  const [planContent, setPlanContent] = useState<string>('');
  const [logsContent, setLogsContent] = useState<string>('');
  const [logsAutoScroll, setLogsAutoScroll] = useState(true);
  const logsRef = useRef<HTMLDivElement>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Bottom panel state
  const [panelOpen, setPanelOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('workflow-panel-open');
      return saved !== null ? saved === 'true' : true;
    }
    return true;
  });
  const [panelHeight, setPanelHeight] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('workflow-panel-height');
      return saved ? parseInt(saved, 10) : DEFAULT_PANEL_HEIGHT;
    }
    return DEFAULT_PANEL_HEIGHT;
  });
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef<{ startY: number; startHeight: number } | null>(null);

  // Persist panel state
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('workflow-panel-open', String(panelOpen));
    }
  }, [panelOpen]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('workflow-panel-height', String(panelHeight));
    }
  }, [panelHeight]);

  const fetchWorkflows = useCallback(async () => {
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_LIST}`);
      if (!response.ok) {
        throw new Error('Failed to fetch workflows');
      }
      const data = await response.json();
      setWorkflows(data.workflows || []);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workflows');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchWorkflowDetail = useCallback(async (workflowId: string) => {
    setDetailLoading(true);
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_DETAIL}/${workflowId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch workflow details');
      }
      const data = await response.json();
      if (data.error) {
        throw new Error(data.error);
      }
      setWorkflowDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workflow details');
      setWorkflowDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const fetchPlan = useCallback(async (workflowId: string) => {
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_DETAIL}/${workflowId}/plan`);
      if (!response.ok) return;
      const data = await response.json();
      if (data.content) {
        setPlanContent(data.content);
      }
    } catch {
      setPlanContent('Failed to load plan');
    }
  }, []);

  const fetchLogs = useCallback(async (workflowId: string) => {
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_DETAIL}/${workflowId}/logs?lines=200`);
      if (!response.ok) return;
      const data = await response.json();
      setLogsContent(data.logs || 'No logs available');
      if (logsAutoScroll && logsRef.current) {
        logsRef.current.scrollTop = logsRef.current.scrollHeight;
      }
    } catch {
      setLogsContent('Failed to load logs');
    }
  }, [logsAutoScroll]);

  const startWorkflow = useCallback(async (workflowId: string) => {
    setIsStarting(true);
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_DETAIL}/${workflowId}/start`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.error) {
        console.error('Failed to start workflow:', data.error);
      } else {
        setIsRunning(true);
        // Switch to graph tab to show progress
        setActiveTab('graph');
      }
    } catch (err) {
      console.error('Failed to start workflow:', err);
    } finally {
      setIsStarting(false);
    }
  }, []);

  const stopWorkflow = useCallback(async (workflowId: string) => {
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_DETAIL}/${workflowId}/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.error) {
        console.error('Failed to stop workflow:', data.error);
      } else {
        setIsRunning(false);
      }
    } catch (err) {
      console.error('Failed to stop workflow:', err);
    }
  }, []);

  const deleteWorkflow = useCallback(async (workflowId: string) => {
    setIsDeleting(true);
    try {
      const response = await fetch(`${HTTP_PROXY_PATH}${WORKFLOWS_DETAIL}/${workflowId}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (data.error) {
        console.error('Failed to delete workflow:', data.error);
      } else {
        setWorkflows(prev => prev.filter(wf => wf.id !== workflowId));
        setSelectedWorkflow(null);
        setWorkflowDetail(null);
        setShowDeleteConfirm(false);
      }
    } catch (err) {
      console.error('Failed to delete workflow:', err);
    } finally {
      setIsDeleting(false);
    }
  }, []);

  // Resize handlers
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeRef.current = { startY: e.clientY, startHeight: panelHeight };
  }, [panelHeight]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !resizeRef.current) return;
      const delta = resizeRef.current.startY - e.clientY;
      const newHeight = Math.min(MAX_PANEL_HEIGHT, Math.max(MIN_PANEL_HEIGHT, resizeRef.current.startHeight + delta));
      setPanelHeight(newHeight);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      resizeRef.current = null;
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'ns-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  // Initial load and polling for workflow list
  useEffect(() => {
    fetchWorkflows();
    const interval = setInterval(fetchWorkflows, 5000);
    return () => clearInterval(interval);
  }, [fetchWorkflows]);

  // Fetch detail when workflow selected
  useEffect(() => {
    if (selectedWorkflow) {
      fetchWorkflowDetail(selectedWorkflow);
      fetchPlan(selectedWorkflow);
      fetchLogs(selectedWorkflow);

      const detailInterval = setInterval(() => fetchWorkflowDetail(selectedWorkflow), 2000);
      const logsInterval = setInterval(() => fetchLogs(selectedWorkflow), 2000);

      return () => {
        clearInterval(detailInterval);
        clearInterval(logsInterval);
      };
    } else {
      setIsRunning(false);
    }
  }, [selectedWorkflow, fetchWorkflowDetail, fetchPlan, fetchLogs]);

  // Sync isRunning from API response
  useEffect(() => {
    if (workflowDetail?.process_running !== undefined) {
      setIsRunning(workflowDetail.process_running);
    }
  }, [workflowDetail?.process_running]);

  const TabButton = ({ tab, icon, label }: { tab: TabType; icon: React.ReactNode; label: string }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
        activeTab === tab
          ? 'bg-white dark:bg-[#343541] text-purple-600 dark:text-purple-400 border-b-2 border-purple-500'
          : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
      }`}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#343541] pt-3">
      {/* Header */}
      <div className="bg-white dark:bg-[#202123] border-b border-gray-200 dark:border-gray-700 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <IconListCheck className="text-purple-500" size={28} />
            <div>
              <h1 className="text-xl font-bold text-gray-800 dark:text-gray-100">
                Workflows
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Calibration workflow status and progress
              </p>
            </div>
          </div>

          {/* Selected workflow info - right side */}
          <div className="flex items-center gap-6">
            {workflowDetail && (
              <div className="flex items-center gap-4 border-r border-gray-200 dark:border-gray-700 pr-6">
                <div className="text-right">
                  <div className="font-medium text-gray-800 dark:text-gray-100">
                    {workflowDetail.name}
                  </div>
                  {workflowDetail.objective && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 max-w-xs truncate">
                      {workflowDetail.objective}
                    </div>
                  )}
                </div>
                <span
                  className={`px-2 py-0.5 text-xs rounded-full text-white whitespace-nowrap ${
                    STATUS_COLORS[workflowDetail.status] || 'bg-gray-500'
                  }`}
                >
                  {workflowDetail.status.toUpperCase()}
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                  {workflowDetail.progress.completed}/{workflowDetail.progress.total} nodes
                </span>
              </div>
            )}
            <div className="flex items-center gap-4">
              {lastUpdated && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Updated: {lastUpdated.toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={() => {
                  fetchWorkflows();
                  if (selectedWorkflow) {
                    fetchWorkflowDetail(selectedWorkflow);
                    fetchLogs(selectedWorkflow);
                  }
                }}
                disabled={loading}
                className={`p-2 rounded-lg transition-colors ${
                  loading
                    ? 'bg-gray-100 dark:bg-gray-800 cursor-not-allowed'
                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
                title="Refresh"
              >
                <IconRefresh
                  size={18}
                  className={`text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`}
                />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Workflow List */}
        <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-[#202123] flex flex-col overflow-y-auto">
          {error && (
            <div className="m-2 p-2 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded">
              <p className="text-red-700 dark:text-red-300 text-xs">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              Loading workflows...
            </div>
          ) : workflows.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              No workflows found
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {workflows.map((wf) => (
                <div
                  key={wf.workflow_id}
                  onClick={() => {
                    setSelectedWorkflow(wf.workflow_id);
                    setActiveTab('graph');
                    setShowDeleteConfirm(false);
                  }}
                  className={`p-4 cursor-pointer transition-colors ${
                    selectedWorkflow === wf.workflow_id
                      ? 'bg-purple-100 dark:bg-purple-900/30 border-l-4 border-purple-500'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-700 dark:text-gray-300 truncate">
                      {wf.name || wf.workflow_id}
                    </span>
                    {(() => {
                      const displayStatus = getDisplayStatus(wf.status, wf.process_running);
                      return (
                        <span
                          className={`flex-shrink-0 ml-2 px-2 py-0.5 text-xs rounded-full text-white ${
                            STATUS_COLORS[displayStatus] || 'bg-gray-500'
                          } ${displayStatus === 'executing' ? 'animate-pulse' : ''}`}
                        >
                          {displayStatus}
                        </span>
                      );
                    })()}
                  </div>
                  <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Progress: {wf.progress}
                    {wf.current_node && (
                      <span className="ml-2">
                        <IconChevronRight className="w-3 h-3 inline" />
                        {wf.current_node}
                      </span>
                    )}
                  </div>
                  {/* Progress bar */}
                  <div className="mt-2 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-green-500 transition-all duration-300"
                      style={{ width: `${wf.total > 0 ? (wf.completed / wf.total) * 100 : 0}%` }}
                    />
                    <div
                      className="h-full bg-red-500 transition-all duration-300"
                      style={{ width: `${wf.total > 0 ? (wf.failed / wf.total) * 100 : 0}%` }}
                    />
                    <div
                      className="h-full bg-blue-500 transition-all duration-300 animate-pulse"
                      style={{ width: `${wf.total > 0 ? (wf.running / wf.total) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Panel - Workflow Detail */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white dark:bg-[#343541] relative">
          {!selectedWorkflow ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <IconListCheck className="mx-auto text-gray-400 mb-4" size={48} />
                <p className="text-gray-500 dark:text-gray-400">
                  Select a workflow to view details
                </p>
              </div>
            </div>
          ) : detailLoading && !workflowDetail ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">
                  Loading workflow details...
                </p>
              </div>
            </div>
          ) : !workflowDetail ? (
            <div className="h-full flex items-center justify-center text-red-500">
              Failed to load workflow details
            </div>
          ) : (
            <>
              {/* Tabs */}
              <div className="flex gap-1 px-6 pt-4 bg-gray-50 dark:bg-[#202123] border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
                <TabButton tab="graph" icon={<IconGitBranch size={16} />} label="Graph" />
                <TabButton tab="nodes" icon={<IconLayoutList size={16} />} label="Status" />
                <TabButton tab="plan" icon={<IconFileText size={16} />} label="Plan" />

                {/* Spacer */}
                <div className="flex-1" />

                {/* Delete Button */}
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={isRunning}
                  className="flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  title={isRunning ? 'Stop workflow before deleting' : 'Delete workflow'}
                >
                  <IconTrash size={16} />
                </button>

                {/* Start/Stop Button */}
                {isRunning ? (
                  <button
                    onClick={() => selectedWorkflow && stopWorkflow(selectedWorkflow)}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-red-500 hover:bg-red-600 text-white transition-colors"
                  >
                    <IconPlayerStop size={16} />
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={() => selectedWorkflow && startWorkflow(selectedWorkflow)}
                    disabled={isStarting}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isStarting ? (
                      <IconLoader size={16} className="animate-spin" />
                    ) : (
                      <IconPlayerPlay size={16} />
                    )}
                    {isStarting ? 'Starting...' : 'Start'}
                  </button>
                )}
              </div>

              {/* Delete Confirmation Dialog */}
              {showDeleteConfirm && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/30 dark:bg-black/50 rounded-lg">
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 p-6 max-w-sm mx-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 rounded-full bg-red-100 dark:bg-red-900/30">
                        <IconTrash size={20} className="text-red-500" />
                      </div>
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                        Delete Workflow
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Delete workflow <span className="font-semibold text-gray-800 dark:text-gray-200">{workflowDetail?.name}</span>?
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mb-5">
                      This will permanently remove the workflow and all its data. This cannot be undone.
                    </p>
                    <div className="flex justify-end gap-3">
                      <button
                        autoFocus
                        onClick={() => setShowDeleteConfirm(false)}
                        className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => selectedWorkflow && deleteWorkflow(selectedWorkflow)}
                        disabled={isDeleting}
                        className="px-4 py-2 text-sm font-medium rounded-lg bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-50"
                      >
                        {isDeleting ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab Content */}
              <div className="flex-1 overflow-hidden">
                {activeTab === 'graph' && (
                  <div className="h-full w-full">
                    {workflowDetail.nodes.length === 0 ? (
                      <div className="h-full flex items-center justify-center text-gray-500">
                        No nodes to display
                      </div>
                    ) : (
                      <WorkflowGraph nodes={workflowDetail.nodes} />
                    )}
                  </div>
                )}

                {activeTab === 'nodes' && (
                  <div className="h-full overflow-y-auto p-6">
                    <div className="space-y-6 max-w-4xl">
                      {/* Nodes */}
                      <div className="p-4 rounded-lg bg-gray-50 dark:bg-[#202123]">
                        <h3 className="font-medium text-gray-800 dark:text-gray-200 mb-3">Nodes</h3>
                        <div className="space-y-2">
                          {workflowDetail.nodes.map((node) => (
                            <div
                              key={node.id}
                              className={`p-3 rounded-lg border ${
                                node.state === 'running'
                                  ? 'border-blue-500/50 bg-blue-50 dark:bg-blue-900/20'
                                  : 'border-gray-200 dark:border-gray-700'
                              }`}
                            >
                              <div className="flex items-start gap-3">
                                <div className="pt-0.5">{NODE_ICONS[node.state]}</div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between">
                                    <span className="font-medium text-gray-700 dark:text-gray-300">
                                      {node.name}
                                    </span>
                                    <span className="text-xs text-gray-500">{node.id}</span>
                                  </div>
                                  {node.run_count > 0 && (
                                    <div className="text-xs text-gray-500">
                                      Run {node.run_count}
                                      {node.state === 'running' && ' (in progress)'}
                                    </div>
                                  )}
                                  {node.extracted && Object.keys(node.extracted).length > 0 && (
                                    <div className="mt-2">
                                      <div className="text-xs text-gray-500">Extracted:</div>
                                      <div className="text-sm font-mono text-gray-700 dark:text-gray-300">
                                        {Object.entries(node.extracted).map(([key, value]) => (
                                          <div key={key}>
                                            {key}: {typeof value === 'number' ? value.toFixed(4) : String(value)}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                                {node.experiment_id && (
                                  <div className="flex-shrink-0">
                                    <NodePlot experimentId={node.experiment_id} />
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'plan' && (
                  <div className="h-full flex flex-col p-6">
                    <div
                      className="flex-1 p-4 rounded-lg bg-gray-50 dark:bg-[#202123] overflow-auto"
                    >
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{planContent || 'No plan available'}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}

              </div>

              {/* Resize Divider */}
              <div
                onMouseDown={handleResizeStart}
                className={`h-1 bg-gray-200 dark:bg-gray-700 cursor-ns-resize hover:bg-purple-400 dark:hover:bg-purple-600 transition-colors flex-shrink-0 ${
                  isResizing ? 'bg-purple-500' : ''
                }`}
              />

              {/* Bottom Panel - Context & History */}
              <div
                className="flex-shrink-0 bg-gray-50 dark:bg-[#1a1a1a] border-t border-gray-200 dark:border-gray-700 flex flex-col"
                style={{ height: panelOpen ? panelHeight : 36 }}
              >
                {/* Panel Header */}
                <div
                  onClick={() => setPanelOpen(!panelOpen)}
                  className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-[#202123] cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors flex-shrink-0"
                >
                  <div className="flex items-center gap-4">
                    {panelOpen ? (
                      <IconChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <IconChevronUp className="w-4 h-4 text-gray-500" />
                    )}
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Context & Logs
                    </span>
                  </div>
                  {panelOpen && (
                    <label className="flex items-center gap-2 text-xs text-gray-500" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={logsAutoScroll}
                        onChange={(e) => setLogsAutoScroll(e.target.checked)}
                        className="rounded w-3 h-3"
                      />
                      Auto-scroll
                    </label>
                  )}
                </div>

                {/* Panel Content - Resizable Split View */}
                {panelOpen && (
                  <PanelGroup direction="horizontal" className="flex-1">
                    {/* Left: Context */}
                    <Panel defaultSize={30} minSize={15} maxSize={50}>
                      <div className="h-full overflow-y-auto px-4 py-2">
                        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Context</div>
                        {workflowDetail.context && Object.keys(workflowDetail.context).length > 0 ? (
                          <div className="font-mono text-xs space-y-1">
                            {Object.entries(workflowDetail.context).map(([key, value]) => (
                              <div key={key} className="flex justify-between gap-2">
                                <span className="text-gray-600 dark:text-gray-400">{key}:</span>
                                <span className="text-gray-800 dark:text-gray-200 text-right">
                                  {typeof value === 'number' ? value.toFixed(4) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-gray-500 dark:text-gray-400 text-xs">No context</div>
                        )}
                      </div>
                    </Panel>

                    <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-purple-400 dark:hover:bg-purple-600 transition-colors cursor-col-resize" />

                    {/* Right: Logs */}
                    <Panel defaultSize={70} minSize={30}>
                      <div
                        ref={logsRef}
                        className="h-full overflow-auto px-4 py-2 bg-white dark:bg-[#1a1a1a] font-mono"
                      >
                        {logsContent ? (
                          parseLogLines(logsContent).map((entry, idx) => (
                            <LogEntryDisplay key={idx} entry={entry} />
                          ))
                        ) : (
                          <div className="text-gray-500 dark:text-gray-400 text-xs">No logs available</div>
                        )}
                      </div>
                    </Panel>
                  </PanelGroup>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
