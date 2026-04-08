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

import React, { useState, useMemo } from 'react';
import { IconChevronDown, IconChevronRight, IconCalendar } from '@tabler/icons-react';
import { ExperimentListItem } from '@/types/qcal';

interface ExperimentListProps {
  experiments: ExperimentListItem[];
  selectedExperimentId?: string;
  onSelectExperiment: (experimentId: string) => void;
  loading?: boolean;
  error?: string;
}

interface GroupedExperiments {
  [date: string]: ExperimentListItem[];
}

export const ExperimentList: React.FC<ExperimentListProps> = ({
  experiments,
  selectedExperimentId,
  onSelectExperiment,
  loading,
  error
}) => {
  const [filterType, setFilterType] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());

  const groupedExperiments = useMemo(() => {
    const groups: GroupedExperiments = {};

    experiments.forEach(exp => {
      if (exp.timestamp) {
        const date = new Date(exp.timestamp);
        const dateKey = date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });

        if (!groups[dateKey]) {
          groups[dateKey] = [];
        }
        groups[dateKey].push(exp);
      }
    });

    Object.keys(groups).forEach(date => {
      groups[date].sort((a, b) => {
        const timeA = new Date(a.timestamp || 0).getTime();
        const timeB = new Date(b.timestamp || 0).getTime();
        return timeB - timeA;
      });
    });

    return groups;
  }, [experiments]);

  const sortedDates = useMemo(() => {
    return Object.keys(groupedExperiments).sort((a, b) => {
      const dateA = new Date(groupedExperiments[a][0].timestamp || 0).getTime();
      const dateB = new Date(groupedExperiments[b][0].timestamp || 0).getTime();
      return dateB - dateA;
    });
  }, [groupedExperiments]);

  useMemo(() => {
    if (sortedDates.length > 0 && expandedDates.size === 0) {
      setExpandedDates(new Set(sortedDates));
    }
  }, [sortedDates]);

  const uniqueTypes = useMemo(() => {
    const types = new Set<string>();
    experiments.forEach(exp => types.add(exp.type));
    return Array.from(types).sort();
  }, [experiments]);

  const filteredGroupedExperiments = useMemo(() => {
    const filtered: GroupedExperiments = {};

    Object.entries(groupedExperiments).forEach(([date, exps]) => {
      const filteredExps = exps.filter(exp => {
        const matchesType = filterType === 'all' || exp.type === filterType;
        const matchesStatus = filterStatus === 'all' || exp.status === filterStatus;
        return matchesType && matchesStatus;
      });

      if (filteredExps.length > 0) {
        filtered[date] = filteredExps;
      }
    });

    return filtered;
  }, [groupedExperiments, filterType, filterStatus]);

  const toggleDateExpansion = (date: string) => {
    const newExpanded = new Set(expandedDates);
    if (newExpanded.has(date)) {
      newExpanded.delete(date);
    } else {
      newExpanded.add(date);
    }
    setExpandedDates(newExpanded);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return '✓';
      case 'failed': return '✗';
      default: return '•';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-600 dark:text-green-400';
      case 'failed': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const formatTime = (timestamp?: string) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    } catch {
      return 'N/A';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading experiments...</div>
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

  const filteredDates = Object.keys(filteredGroupedExperiments).sort((a, b) => {
    const dateA = new Date(filteredGroupedExperiments[a][0].timestamp || 0).getTime();
    const dateB = new Date(filteredGroupedExperiments[b][0].timestamp || 0).getTime();
    return dateB - dateA;
  });

  const totalFilteredExperiments = Object.values(filteredGroupedExperiments)
    .reduce((sum, exps) => sum + exps.length, 0);

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-300 dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">Experiments</h2>

        <div className="space-y-2">
          <select
            className="w-full px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-[#343541]"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="all">All Types</option>
            {uniqueTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <select
            className="w-full px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-[#343541]"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
          Showing {totalFilteredExperiments} of {experiments.length} experiments
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {filteredDates.length === 0 ? (
          <div className="p-4 text-center text-gray-600 dark:text-gray-400">
            No experiments found
          </div>
        ) : (
          <div>
            {filteredDates.map(date => {
              const dateExperiments = filteredGroupedExperiments[date];
              const isExpanded = expandedDates.has(date);

              return (
                <div key={date} className="border-b border-gray-200 dark:border-gray-700">
                  <div
                    className="px-4 py-2 bg-gray-50 dark:bg-[#2a2b32] hover:bg-gray-100 dark:hover:bg-[#343541] cursor-pointer flex items-center justify-between"
                    onClick={() => toggleDateExpansion(date)}
                  >
                    <div className="flex items-center">
                      {isExpanded ? (
                        <IconChevronDown size={16} className="mr-2 text-gray-500 dark:text-gray-400" />
                      ) : (
                        <IconChevronRight size={16} className="mr-2 text-gray-500 dark:text-gray-400" />
                      )}
                      <span className="font-medium text-gray-900 dark:text-gray-100">{date}</span>
                    </div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {dateExperiments.length} experiment{dateExperiments.length !== 1 ? 's' : ''}
                    </span>
                  </div>

                  {isExpanded && (
                    <div>
                      {dateExperiments.map(exp => (
                        <div
                          key={exp.id}
                          className={`px-4 py-3 hover:bg-gray-50 dark:hover:bg-[#2a2b32] cursor-pointer transition-colors border-l-4 ${
                            selectedExperimentId === exp.id
                              ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500'
                              : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
                          }`}
                          onClick={() => onSelectExperiment(exp.id)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
                                  {exp.type}
                                </span>
                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                  {formatTime(exp.timestamp)}
                                </span>
                              </div>
                              <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                ID: {exp.id.substring(0, 24)}...
                              </div>
                            </div>
                            <div className={`ml-2 ${getStatusColor(exp.status)}`}>
                              <span className="text-lg">{getStatusIcon(exp.status)}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
