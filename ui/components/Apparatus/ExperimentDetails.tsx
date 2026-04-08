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

import React from 'react';
import {
  IconFlask,
  IconInfoCircle,
  IconCode,
  IconFolder,
  IconFileText,
  IconCopy,
  IconArrowRight
} from '@tabler/icons-react';
import { ExperimentSchema } from '@/types/qcal';

interface ExperimentDetailsProps {
  experimentName: string;
  experimentData?: ExperimentSchema;
  onViewSource?: () => void;
  showViewSourceButton?: boolean;
}

export const ExperimentDetails: React.FC<ExperimentDetailsProps> = ({
  experimentName,
  experimentData,
  onViewSource,
  showViewSourceButton
}) => {
  if (!experimentName) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <IconFlask size={48} className="mx-auto mb-4 opacity-50" />
          <p>Select an experiment to view its details</p>
        </div>
      </div>
    );
  }

  if (!experimentData) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <IconInfoCircle size={48} className="mx-auto mb-4 opacity-50" />
          <p>No experiment data available</p>
          <p className="text-sm mt-2">Experiment server may be disconnected</p>
        </div>
      </div>
    );
  }

  const handleCopyPath = (path: string) => {
    if (!path || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return;
    navigator.clipboard.writeText(path).catch(() => {});
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-gray-700 pb-4 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                {experimentData.name}
              </h2>
              <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                <span className="flex items-center gap-1">
                  <IconFolder size={16} />
                  Experiment
                </span>
                <span className="flex items-center gap-1">
                  <IconCode size={16} />
                  {experimentName}
                </span>
              </div>
            </div>
            <IconFlask size={32} className="text-purple-500" />
          </div>
        </div>

        {/* Description Section */}
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
            <IconInfoCircle size={20} />
            Description
          </h3>
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <p className="text-gray-700 dark:text-gray-300">
              {experimentData.description || 'No description available for this experiment.'}
            </p>
          </div>
        </div>

        {/* Source File Section */}
        {experimentData.module_path && (
          <div className="mb-6">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
              <IconFileText size={20} />
              Source File
            </h3>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300 break-all">
                  <IconFileText size={18} className="flex-shrink-0 mt-0.5" />
                  <span className="font-mono">{experimentData.module_path}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleCopyPath(experimentData.module_path)}
                  className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                  aria-label="Copy source file path"
                >
                  <IconCopy size={16} />
                  Copy
                </button>
              </div>
              {showViewSourceButton && onViewSource && (
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={onViewSource}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors text-sm font-medium"
                  >
                    <IconCode size={18} />
                    View Source
                    <IconArrowRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Parameters Section */}
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
            <IconCode size={20} />
            Input Parameters
          </h3>
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            {experimentData.parameters && experimentData.parameters.length > 0 ? (
              <div className="space-y-3">
                {experimentData.parameters.map((param, idx) => (
                  <div key={idx} className="border-b border-gray-200 dark:border-gray-700 last:border-0 pb-3 last:pb-0">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-gray-700 dark:text-gray-300">
                            {param.name}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">
                            {param.type}
                          </span>
                          {param.required && (
                            <span className="text-xs text-red-500 font-semibold">*required</span>
                          )}
                        </div>
                        {param.range && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            Range: {param.range[0]} to {param.range[1]}
                          </p>
                        )}
                      </div>
                      {param.default !== undefined && param.default !== null && (
                        <div className="ml-4 text-sm text-gray-500 dark:text-gray-400">
                          <span className="font-medium">Default: </span>
                          <code className="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded">
                            {String(param.default)}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 italic">
                No input parameters required for this experiment.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
