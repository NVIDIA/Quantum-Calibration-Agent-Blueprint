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

// =============================================================================
// Application Information
// =============================================================================

const APPLICATION_NAME = 'Quantum Calibration Agent';
const APPLICATION_UI_NAME = 'Quantum Calibration Agent UI';
const botHeader = 'Scout Bot';

// =============================================================================
// Security & Session
// =============================================================================

const SESSION_COOKIE_NAME = 'qca-session';
const MAX_FILE_SIZE_BYTES = 5242880; // 5MB

// =============================================================================
// Proxy & Routing Configuration
// =============================================================================

const HTTP_PROXY_PATH = process.env.HTTP_PUBLIC_PATH || '/api';
const WEBSOCKET_PROXY_PATH = process.env.WS_PUBLIC_PATH || '/ws';
const WEBSOCKET_BACKEND_PATH = '/websocket';

// =============================================================================
// API Routes
// =============================================================================
const CHAT_STREAM = '/chat/stream';
const CHAT = '/chat';
const CHAT_RESUME = '/chat/resume';
const GENERATE_STREAM = '/generate/stream';
const GENERATE = '/generate';
const CA_RAG_INIT = '/init';
const CHAT_CA_RAG = '/call';
const UPDATE_DATA_STREAM = '/update-data-stream';
const MCP_CLIENT_TOOL_LIST = '/mcp/client/tool/list';
const FEEDBACK = '/feedback';

// =============================================================================
// Route Collections
// =============================================================================

const CORE_ROUTES = {
  CHAT_STREAM,
  CHAT,
  CHAT_RESUME,
  GENERATE_STREAM,
  GENERATE,
  MCP_CLIENT_TOOL_LIST,
};

// Experiment/Apparatus routes
const EXPERIMENT_CAPABILITIES = '/experiment/capabilities';
const EXPERIMENT_SCHEMA = '/experiment/schema';
const EXPERIMENT_SCRIPT = '/experiment/script';
const HISTORY_LIST = '/history/list';
const HISTORY_DETAIL = '/history';

// Knowledge routes (read-only)
const KNOWLEDGE_LIST = '/knowledge/list';
const KNOWLEDGE_READ = '/knowledge/read';

// Workflow routes
const WORKFLOWS_LIST = '/workflows/list';
const WORKFLOWS_DETAIL = '/workflows';
const WORKFLOWS_HISTORY = '/workflows';

const EXTENDED_ROUTES = {
  CA_RAG_INIT,
  CHAT_CA_RAG,
  UPDATE_DATA_STREAM,
  FEEDBACK,
  EXPERIMENT_CAPABILITIES,
  EXPERIMENT_SCHEMA,
  EXPERIMENT_SCRIPT,
  HISTORY_LIST,
  HISTORY_DETAIL,
  KNOWLEDGE_LIST,
  KNOWLEDGE_READ,
  WORKFLOWS_LIST,
  WORKFLOWS_DETAIL,
  WORKFLOWS_HISTORY,
};

const EXTENDED_BACKEND_TARGETS = {
  [CA_RAG_INIT]: 'NAT_BACKEND',
  [CHAT_CA_RAG]: 'NAT_BACKEND',
  [UPDATE_DATA_STREAM]: 'NEXTJS',
  [FEEDBACK]: 'NAT_BACKEND',
  [EXPERIMENT_CAPABILITIES]: 'NAT_BACKEND',
  [EXPERIMENT_SCHEMA]: 'NAT_BACKEND',
  [EXPERIMENT_SCRIPT]: 'NAT_BACKEND',
  [HISTORY_LIST]: 'NAT_BACKEND',
  [HISTORY_DETAIL]: 'NAT_BACKEND',
  [KNOWLEDGE_LIST]: 'NAT_BACKEND',
  [KNOWLEDGE_READ]: 'NAT_BACKEND',
  [WORKFLOWS_LIST]: 'NAT_BACKEND',
  [WORKFLOWS_DETAIL]: 'NAT_BACKEND',
  [WORKFLOWS_HISTORY]: 'NAT_BACKEND',
};

// =============================================================================
// Route UI Configuration
// =============================================================================

const CORE_ROUTE_OPTIONS = [
  { label: 'Chat Completions — Streaming', value: CHAT_STREAM },
  { label: 'Chat Completions — Non-Streaming', value: CHAT },
  { label: 'Generate — Streaming', value: GENERATE_STREAM },
  { label: 'Generate — Non-Streaming', value: GENERATE },
  {
    label: 'Context-Aware RAG — Non-Streaming (Experimental)',
    value: CHAT_CA_RAG,
  },
];

const DEFAULT_CORE_ROUTE = CHAT_STREAM;

// =============================================================================
// Security & Validation
// =============================================================================

const ALLOWED_PATHS = [
  ...Object.values(CORE_ROUTES),
  ...Object.values(EXTENDED_ROUTES),
];

// =============================================================================
// HTTP Methods
// =============================================================================

const HTTP_METHOD_GET = 'GET';
const HTTP_METHOD_POST = 'POST';
const HTTP_METHOD_PUT = 'PUT';
const HTTP_METHOD_DELETE = 'DELETE';
const HTTP_METHOD_OPTIONS = 'OPTIONS';

// =============================================================================
// HTTP Headers
// =============================================================================

const HTTP_HEADER_CONTENT_TYPE = 'Content-Type';
const HTTP_HEADER_AUTHORIZATION = 'Authorization';
const HTTP_HEADER_CONVERSATION_ID = 'Conversation-Id';
const HTTP_HEADER_TIMEZONE = 'X-Timezone';
const HTTP_HEADER_USER_MESSAGE_ID = 'User-Message-ID';

// =============================================================================
// CORS Configuration
// =============================================================================

const CORS_METHODS = [
  HTTP_METHOD_GET,
  HTTP_METHOD_POST,
  HTTP_METHOD_PUT,
  HTTP_METHOD_DELETE,
  HTTP_METHOD_OPTIONS,
].join(', ');

const CORS_HEADERS = [
  HTTP_HEADER_CONTENT_TYPE,
  HTTP_HEADER_AUTHORIZATION,
  HTTP_HEADER_CONVERSATION_ID,
  HTTP_HEADER_TIMEZONE,
  HTTP_HEADER_USER_MESSAGE_ID,
].join(', ');

const CORS_ORIGIN = process.env.CORS_ORIGIN || 'http://localhost:3000';

module.exports = {
  APPLICATION_NAME,
  APPLICATION_UI_NAME,
  botHeader,
  SESSION_COOKIE_NAME,
  MAX_FILE_SIZE_BYTES,
  HTTP_PROXY_PATH,
  WEBSOCKET_PROXY_PATH,
  WEBSOCKET_BACKEND_PATH,
  CHAT_STREAM,
  CHAT,
  CHAT_RESUME,
  GENERATE_STREAM,
  GENERATE,
  CA_RAG_INIT,
  CHAT_CA_RAG,
  UPDATE_DATA_STREAM,
  MCP_CLIENT_TOOL_LIST,
  FEEDBACK,
  EXPERIMENT_CAPABILITIES,
  EXPERIMENT_SCHEMA,
  EXPERIMENT_SCRIPT,
  HISTORY_LIST,
  HISTORY_DETAIL,
  KNOWLEDGE_LIST,
  KNOWLEDGE_READ,
  WORKFLOWS_LIST,
  WORKFLOWS_DETAIL,
  WORKFLOWS_HISTORY,
  CORE_ROUTES,
  CORE_ROUTE_OPTIONS,
  DEFAULT_CORE_ROUTE,
  EXTENDED_ROUTES,
  EXTENDED_BACKEND_TARGETS,
  ALLOWED_PATHS,
  HTTP_METHOD_GET,
  HTTP_METHOD_POST,
  HTTP_METHOD_PUT,
  HTTP_METHOD_DELETE,
  HTTP_METHOD_OPTIONS,
  CORS_METHODS,
  HTTP_HEADER_CONTENT_TYPE,
  HTTP_HEADER_AUTHORIZATION,
  HTTP_HEADER_CONVERSATION_ID,
  HTTP_HEADER_TIMEZONE,
  HTTP_HEADER_USER_MESSAGE_ID,
  CORS_HEADERS,
  CORS_ORIGIN,
};
