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

import React, { useState, useEffect, useCallback } from 'react';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';

import { ExperimentListItem, ExperimentResult } from '@/types/qcal';

import { ExperimentList } from './ExperimentList';
import { ExperimentDetails } from './ExperimentDetails';
import { ExperimentPlots } from './ExperimentPlots';

export const Experiments: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentListItem[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | undefined>();
  const [selectedExperiment, setSelectedExperiment] = useState<ExperimentResult | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [listError, setListError] = useState<string | undefined>();
  const [detailsError, setDetailsError] = useState<string | undefined>();
  const [autoRefresh, setAutoRefresh] = useState(false);

  const loadExperiments = useCallback(async () => {
    try {
      setListLoading(true);
      setListError(undefined);

      const response = await fetch('/api/history/list?last=100');
      const data = await response.json();

      if (data.experiments) {
        setExperiments(data.experiments);
      } else if (data.error) {
        setListError(data.error);
      } else {
        setExperiments([]);
      }
    } catch (error: unknown) {
      setListError(error instanceof Error ? error.message : 'Failed to load experiments');
      setExperiments([]);
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    loadExperiments();
  }, [loadExperiments]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadExperiments, 10000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, loadExperiments]);

  useEffect(() => {
    if (!selectedExperimentId) {
      setSelectedExperiment(null);
      return;
    }

    const loadExperimentDetails = async () => {
      try {
        setDetailsLoading(true);
        setDetailsError(undefined);

        const response = await fetch(`/api/history/${encodeURIComponent(selectedExperimentId)}`);
        const data = await response.json();

        if (data.id) {
          setSelectedExperiment(data);
        } else if (data.error) {
          setDetailsError(data.error);
        }
      } catch (error: unknown) {
        setDetailsError(error instanceof Error ? error.message : 'Failed to load experiment details');
      } finally {
        setDetailsLoading(false);
      }
    };

    loadExperimentDetails();
  }, [selectedExperimentId]);

  return (
    <div className="w-full h-full flex flex-col bg-gray-50 dark:bg-[#343541] pt-3">
      {/* Header */}
      <div className="bg-white dark:bg-[#202123] border-b border-gray-300 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Experiments Dashboard</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Monitor and analyze your quantum calibration experiments
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadExperiments}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Refresh
            </button>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Auto-refresh</span>
            </label>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Experiment List */}
        <div className="w-[25%] bg-white dark:bg-[#202123] border-r border-gray-300 dark:border-gray-700">
          <ExperimentList
            experiments={experiments}
            selectedExperimentId={selectedExperimentId}
            onSelectExperiment={setSelectedExperimentId}
            loading={listLoading}
            error={listError}
          />
        </div>

        {/* Right Panel - Details and Plots */}
        <div className="flex-1 flex flex-col">
          <PanelGroup direction="vertical" className="flex-1 min-h-0">
            <Panel defaultSize={40} minSize={20} maxSize={80} className="bg-white dark:bg-[#202123] min-h-0">
              <ExperimentDetails
                experiment={selectedExperiment}
                loading={detailsLoading}
                error={detailsError}
              />
            </Panel>
            <PanelResizeHandle className="h-1 bg-gray-300 dark:bg-gray-700 hover:bg-blue-500 dark:hover:bg-blue-500 transition-colors cursor-row-resize" />
            <Panel defaultSize={60} minSize={20} maxSize={80} className="bg-white dark:bg-[#202123] min-h-0">
              <ExperimentPlots
                experiment={selectedExperiment}
                loading={detailsLoading}
                error={detailsError}
              />
            </Panel>
          </PanelGroup>
        </div>
      </div>

      {/* Status Bar */}
      <div className="bg-gray-100 dark:bg-[#202123] border-t border-gray-300 dark:border-gray-700 px-6 py-2">
        <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
          <div>
            {experiments.length} experiment{experiments.length !== 1 ? 's' : ''} loaded
            {selectedExperimentId && ` • Viewing: ${selectedExperimentId}`}
          </div>
          <div>
            {autoRefresh && <span className="text-green-600 dark:text-green-400">● Auto-refresh enabled</span>}
          </div>
        </div>
      </div>
    </div>
  );
};
