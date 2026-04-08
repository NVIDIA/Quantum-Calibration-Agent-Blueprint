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

export const CHAT_OPTIONAL_GENERATION_RESERVED_FIELDS = [
  'messages',
  'stream',
] as const;

export const WEBSOCKET_CUSTOM_PARAMS_TOP_KEYS = [
  'query',
  'headers',
  'payload',
] as const;

export const WEBSOCKET_QUERY_RESERVED_KEYS = [
  'session',
  'conversation_id',
] as const;

export const WEBSOCKET_PAYLOAD_RESERVED_KEYS = [
  'type',
  'id',
  'conversation_id',
  'content',
  'schema_type',
  'thread_id',
  'parent_id',
  'timestamp',
] as const;

export function validateOptionalGenerationJson(
  jsonString: string,
): { isValid: boolean; error: string } {
  if (!jsonString.trim()) {
    return { isValid: true, error: '' };
  }

  try {
    const parsed = JSON.parse(jsonString);

    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return { isValid: false, error: 'JSON must be a valid object (not array or null)' };
    }

    const optionalReserved = new Set<string>(CHAT_OPTIONAL_GENERATION_RESERVED_FIELDS);
    const conflictingFields = Object.keys(parsed).filter((key) =>
      optionalReserved.has(key),
    );

    if (conflictingFields.length > 0) {
      return {
        isValid: false,
        error: `Cannot override reserved fields: ${conflictingFields.join(', ')}`,
      };
    }

    return { isValid: true, error: '' };
  } catch {
    return { isValid: false, error: 'Invalid JSON format' };
  }
}

export function validateWebSocketCustomParams(
  jsonString: string,
): { isValid: boolean; error: string } {
  if (!jsonString.trim()) return { isValid: true, error: '' };
  try {
    const parsed = JSON.parse(jsonString);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return { isValid: false, error: 'Must be a JSON object' };
    }
    const allowedTopKeys = new Set<string>(WEBSOCKET_CUSTOM_PARAMS_TOP_KEYS);
    const extraKeys = Object.keys(parsed).filter((k) => !allowedTopKeys.has(k));
    if (extraKeys.length > 0) {
      return {
        isValid: false,
        error: `Top-level keys must be one of: query, headers, payload. Found: ${extraKeys.join(', ')}`,
      };
    }
    if (parsed.query != null) {
      if (typeof parsed.query !== 'object' || Array.isArray(parsed.query)) {
        return { isValid: false, error: 'query must be an object' };
      }
      const queryReserved = new Set<string>(WEBSOCKET_QUERY_RESERVED_KEYS);
      const used = Object.keys(parsed.query).filter((k) => queryReserved.has(k));
      if (used.length > 0) {
        return {
          isValid: false,
          error: `query: reserved keys (${used.join(', ')}) cannot be used.`,
        };
      }
    }
    if (parsed.headers != null) {
      if (typeof parsed.headers !== 'object' || Array.isArray(parsed.headers)) {
        return { isValid: false, error: 'headers must be an object' };
      }
      const nonString = Object.entries(parsed.headers).find(
        ([, v]) => typeof v !== 'string' && typeof v !== 'number',
      );
      if (nonString) {
        return { isValid: false, error: 'headers values must be strings or numbers.' };
      }
    }
    if (parsed.payload != null) {
      if (typeof parsed.payload !== 'object' || Array.isArray(parsed.payload)) {
        return { isValid: false, error: 'payload must be an object' };
      }
      const payloadReserved = new Set<string>(WEBSOCKET_PAYLOAD_RESERVED_KEYS);
      const payloadUsed = Object.keys(parsed.payload).filter((k) =>
        payloadReserved.has(k),
      );
      if (payloadUsed.length > 0) {
        return {
          isValid: false,
          error: `payload: reserved keys (${payloadUsed.join(', ')}) cannot be used.`,
        };
      }
    }
    return { isValid: true, error: '' };
  } catch {
    return { isValid: false, error: 'Invalid JSON' };
  }
}
