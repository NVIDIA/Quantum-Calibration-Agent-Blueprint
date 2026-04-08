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

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { ExperimentResult, PlotData } from '@/types/qcal';

// @ts-ignore - react-plotly.js types are incomplete
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false }) as any;

interface ExperimentPlotsProps {
  experiment: ExperimentResult | null;
  loading?: boolean;
  error?: string;
}

export const ExperimentPlots: React.FC<ExperimentPlotsProps> = ({
  experiment,
  loading,
  error
}) => {
  const [selectedPlotIndex, setSelectedPlotIndex] = useState(0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading plots...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
          Error: {error}
        </div>
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400">Select an experiment to view plots</div>
      </div>
    );
  }

  const plots = experiment.plots || [];

  if (plots.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400">No plots available for this experiment</div>
      </div>
    );
  }

  const currentPlot = plots[selectedPlotIndex];

  return (
    <div className="h-full flex flex-col">
      {/* Header with tabs if multiple plots */}
      {plots.length > 1 && (
        <div className="border-b border-gray-300 dark:border-gray-700">
          <div className="flex overflow-x-auto">
            {plots.map((plot, index) => (
              <button
                key={index}
                className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
                  selectedPlotIndex === index
                    ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'bg-gray-50 dark:bg-[#2a2b32] text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
                onClick={() => setSelectedPlotIndex(index)}
              >
                {plot.name || `Plot ${index + 1}`}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Plot Container */}
      <div className="flex-1 p-4 bg-white dark:bg-[#343541] min-h-0">
        {currentPlot?.data && currentPlot.format === 'plotly' ? (
          <div className="h-full w-full">
            <Plot
              data={currentPlot.data.data || []}
              layout={{
                ...(currentPlot.data.layout || {}),
                autosize: true,
                margin: { t: 40, r: 20, b: 40, l: 60 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#9ca3af' }
              }}
              config={{ responsive: true }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500 dark:text-gray-400">
              {currentPlot?.format === 'png' || currentPlot?.format === 'base64'
                ? 'Image plots not yet supported'
                : 'No plot data available'}
            </div>
          </div>
        )}
      </div>

      {/* Plot Info Footer */}
      <div className="px-4 py-2 bg-gray-50 dark:bg-[#202123] border-t border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center text-xs text-gray-600 dark:text-gray-400">
          <div>
            Plot {selectedPlotIndex + 1} of {plots.length}
            {currentPlot?.name && ` - ${currentPlot.name}`}
          </div>
          <div className="flex gap-2">
            <button
              className="px-2 py-1 bg-white dark:bg-[#343541] border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-[#2a2b32] disabled:opacity-50 text-gray-700 dark:text-gray-300"
              onClick={() => setSelectedPlotIndex(Math.max(0, selectedPlotIndex - 1))}
              disabled={selectedPlotIndex === 0}
            >
              Previous
            </button>
            <button
              className="px-2 py-1 bg-white dark:bg-[#343541] border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-[#2a2b32] disabled:opacity-50 text-gray-700 dark:text-gray-300"
              onClick={() => setSelectedPlotIndex(Math.min(plots.length - 1, selectedPlotIndex + 1))}
              disabled={selectedPlotIndex === plots.length - 1}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
