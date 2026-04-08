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

import { HTTP_PROXY_PATH, MCP_CLIENT_TOOL_LIST } from '@/constants';

export interface MCPTool {
  name: string;
  description: string;
  server: string;
  available: boolean;
}

export interface MCPClient {
  function_group: string;
  server: string;
  transport: string;
  session_healthy: boolean;
  protected?: boolean;
  tools: MCPTool[];
  total_tools: number;
  available_tools: number;
}

export interface MCPClientResponse {
  mcp_clients: MCPClient[];
}

export const fetchMCPClients = async (): Promise<MCPClientResponse> => {
  try {
    // Use server-side API route instead of direct client-side call
    const response = await fetch(`${HTTP_PROXY_PATH}${MCP_CLIENT_TOOL_LIST}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const text = await response.text();
    let body: any = undefined;
    try {
      body = text ? JSON.parse(text) : undefined;
    } catch {
      // ignore JSON parse error; fall back to text
    }

    if (!response.ok) {
      const serverMessage = body?.error || body?.details || text || `HTTP ${response.status}`;
      throw new Error(serverMessage);
    }

    return body as MCPClientResponse;
  } catch (error) {
    console.error('Error fetching MCP clients:', error);
    throw error;
  }
};
