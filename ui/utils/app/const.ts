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

import { MCP_CLIENT_TOOL_LIST, HTTP_PROXY_PATH } from '@/constants';

export const webSocketMessageTypes = {
  userMessage: 'user_message',
  userInteractionMessage: 'user_interaction_message',
  systemResponseMessage: 'system_response_message',
  systemIntermediateMessage: 'system_intermediate_message',
  systemInteractionMessage: 'system_interaction_message',
  oauthConsent: 'oauth_consent',
};

export const appConfig = {
  fileUploadEnabled: false,
};

// MCP API configuration helper
export const getMcpApiUrl = () => {
  const mcpPath = process.env.NEXT_PUBLIC_MCP_PATH || MCP_CLIENT_TOOL_LIST;
  return `${HTTP_PROXY_PATH}${mcpPath}`;
};
