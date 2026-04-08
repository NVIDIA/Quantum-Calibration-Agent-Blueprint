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
 * Request payload builders for backend API routes
 * These functions build endpoint-specific payloads that the UI calls directly
 */

/**
 * Parse optional generation parameters string into object
 * Format: "key1=value1,key2=value2" or JSON string
 * @param {string} paramsString - String containing optional parameters
 * @returns {Object} Object with parsed parameters
 */
function parseOptionalParams(paramsString) {
  if (!paramsString || !paramsString.trim()) {
    return {};
  }

  try {
    // Try parsing as JSON first
    return JSON.parse(paramsString);
  } catch {
    // Fall back to comma-separated key=value format
    const params = {};
    const pairs = paramsString.split(',');

    for (const pair of pairs) {
      const [key, value] = pair.split('=').map((s) => s.trim());
      if (key && value) {
        // Try to parse as number or boolean
        if (value === 'true') params[key] = true;
        else if (value === 'false') params[key] = false;
        else if (!isNaN(Number(value))) params[key] = Number(value);
        else params[key] = value;
      }
    }

    return params;
  }
}

/**
 * Build request payload for /generate/stream endpoint
 * Backend format: {"input_message": "..."}
 *
 * @param {string} message - The user's message content
 * @returns {Object} Backend request payload
 */
function buildGenerateStreamPayload(message) {
  return {
    input_message: message || '',
  };
}

/**
 * Build request payload for /generate endpoint
 * Backend format: {"input_message": "..."}
 *
 * @param {string} message - The user's message content
 * @returns {Object} Backend request payload
 */
function buildGeneratePayload(message) {
  return {
    input_message: message || '',
  };
}

/**
 * Build request payload for /chat endpoint
 * Backend format: {"messages": [...], "model": "...", "stream": false, "temperature": 0.7, ...}
 *
 * @param {Array} messages - Array of message objects with role and content
 * @param {boolean} useChatHistory - Whether to use full chat history or just last message
 * @param {string} optionalParams - Optional generation parameters string
 * @returns {Object} Backend request payload
 */
function buildChatPayload(messages, useChatHistory, optionalParams) {
  // Reserved fields that cannot be overridden by optionalParams
  const RESERVED_FIELDS = ['messages', 'stream'];

  const payload = {
    messages: useChatHistory ? messages : [messages[messages.length - 1]],
    // Let backend use its default model
    stream: false,
    temperature: 0.7,
  };

  // Merge optional generation parameters if provided, filtering out reserved fields
  if (optionalParams && optionalParams.trim()) {
    try {
      const parsedParams = parseOptionalParams(optionalParams);

      // Only merge non-reserved fields
      Object.keys(parsedParams).forEach((key) => {
        if (!RESERVED_FIELDS.includes(key)) {
          payload[key] = parsedParams[key];
        }
      });
    } catch (error) {
      // Silently ignore parse errors - payload will use defaults
    }
  }

  return payload;
}

/**
 * Build request payload for /chat/stream endpoint
 * Backend format: {"messages": [...], "model": "...", "stream": true, "temperature": 0.7, ...}
 *
 * @param {Array} messages - Array of message objects with role and content
 * @param {boolean} useChatHistory - Whether to use full chat history or just last message
 * @param {string} optionalParams - Optional generation parameters string
 * @returns {Object} Backend request payload
 */
function buildChatStreamPayload(messages, useChatHistory, optionalParams) {
  // Reserved fields that cannot be overridden by optionalParams
  const RESERVED_FIELDS = ['messages', 'stream'];

  const payload = {
    messages: useChatHistory ? messages : [messages[messages.length - 1]],
    // Let backend use its default model
    stream: true,
    temperature: 0.7,
  };

  // Merge optional generation parameters if provided, filtering out reserved fields
  if (optionalParams && optionalParams.trim()) {
    try {
      const parsedParams = parseOptionalParams(optionalParams);

      // Only merge non-reserved fields
      Object.keys(parsedParams).forEach((key) => {
        if (!RESERVED_FIELDS.includes(key)) {
          payload[key] = parsedParams[key];
        }
      });
    } catch (error) {
      // Silently ignore parse errors - payload will use defaults
    }
  }

  return payload;
}

/**
 * Build request payload for /call (Context-Aware RAG) endpoint
 * Backend format: {"state": {"chat": {"question": "..."}}}
 *
 * @param {string} message - The user's message content
 * @returns {Object} Backend request payload
 */
function buildCaRagPayload(message) {
  return {
    state: {
      chat: {
        question: message || '',
      },
    },
  };
}

module.exports = {
  buildGenerateStreamPayload,
  buildGeneratePayload,
  buildChatPayload,
  buildChatStreamPayload,
  buildCaRagPayload,
  parseOptionalParams,
};
