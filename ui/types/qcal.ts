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

/**
 * TypeScript types for qcal backend integration.
 */

export interface ParameterSpec {
  name: string;
  type: 'int' | 'float' | 'str' | 'bool' | 'list';
  default?: unknown;
  range?: [number, number];
  required: boolean;
}

export interface ExperimentSchema {
  name: string;
  description: string;
  parameters: ParameterSpec[];
  module_path: string;
}

export interface ExperimentResult {
  id: string;
  type: string;
  timestamp: string;
  status: 'success' | 'failed';
  target?: string;
  params: Record<string, unknown>;
  results: Record<string, unknown>;
  arrays: Record<string, number[]>;
  plots: PlotData[];
  notes: string;
  file_path: string;
}

export interface PlotData {
  name: string;
  format: 'plotly' | 'png' | 'base64';
  data: unknown;
}

export interface ExperimentListItem {
  id: string;
  type: string;
  target?: string;
  timestamp: string;
  status: 'success' | 'failed';
}

export interface ArrayInfo {
  name: string;
  shape: number[];
  dtype: string;
}

export interface ArrayStats {
  min: number;
  max: number;
  mean: number;
  std: number;
  count: number;
}
