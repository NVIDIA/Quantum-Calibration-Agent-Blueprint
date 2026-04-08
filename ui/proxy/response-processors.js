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
 * Response processors for backend API routes
 * Each endpoint has its own processor that handles backend responses
 * and transforms them into client-expected formats
 *
 * Architecture:
 * - Request payload builders (request-transformers.js): UI format → Backend format
 * - Response processors (this file): Backend response → UI format
 */

const constants = require('../constants');

/**
 * Helper function to process intermediate_data lines
 * Parses the intermediate data payload and writes it to the response stream
 * in the format expected by the UI
 *
 * @param {string} line - The line starting with "intermediate_data: "
 * @param {Object} res - The response object to write to
 */
function processIntermediateData(line, res) {
  try {
    const data = line.split('intermediate_data: ')[1];
    const payload = JSON.parse(data);
    const intermediateMessage = {
      id: payload?.id || '',
      status: payload?.status || 'in_progress',
      error: payload?.error || '',
      type: 'system_intermediate',
      parent_id: payload?.parent_id || 'default',
      intermediate_parent_id: payload?.intermediate_parent_id || 'default',
      content: {
        name: payload?.name || 'Step',
        payload: payload?.payload || 'No details',
      },
      time_stamp: payload?.time_stamp || 'default',
    };
    res.write(
      `<intermediatestep>${JSON.stringify(
        intermediateMessage,
      )}</intermediatestep>`,
    );
  } catch (e) {
    // Ignore parse errors
  }
}

function processObservabilityTrace(line, res) {
  try {
    const data = line.split('observability_trace: ')[1];
    const payload = JSON.parse(data);
    if (payload?.observability_trace_id) {
      res.write(
        `<observabilitytraceid>${payload.observability_trace_id}</observabilitytraceid>`,
      );
    }
  } catch (e) {
    // Ignore parse errors
  }
}

/**
 * Process thread_id line from backend
 * Used for conversation continuity and HITL resume
 */
function processThreadId(line, res) {
  try {
    const threadId = line.split('thread_id: ')[1].trim();
    if (threadId) {
      res.write(`<threadid>${threadId}</threadid>`);
    }
  } catch (e) {
    // Ignore parse errors
  }
}

/**
 * Process interrupt line from backend (HITL)
 * Forwards the interrupt payload to the UI for approval/rejection modal
 */
function processInterrupt(line, res) {
  try {
    const data = line.split('interrupt: ')[1];
    const payload = JSON.parse(data);
    // Forward as system_interaction_message for HITL modal
    const interactionMessage = {
      type: 'system_interaction_message',
      id: payload?.interrupt_id || `interrupt_${Date.now()}`,
      thread_id: payload?.thread_id || '',
      content: {
        input_type: 'binary_choice',
        text: formatInterruptText(payload),
        options: [
          { id: 'approve', label: 'Approve', value: 'approve' },
          { id: 'reject', label: 'Reject', value: 'reject' },
        ],
        timeout: 300,
      },
    };
    res.write(
      `<systeminteraction>${JSON.stringify(interactionMessage)}</systeminteraction>`,
    );
  } catch (e) {
    // Ignore parse errors
  }
}

/**
 * Format interrupt actions into readable text
 */
function formatInterruptText(payload) {
  const actions = payload?.actions || [];
  if (actions.length === 0) {
    return 'Approve pending action?';
  }
  const descriptions = actions.map((action) => {
    const name = action.name || 'unknown';
    const desc = action.description || '';
    if (desc) {
      return `**${name}**: ${desc}`;
    }
    const args = action.args || {};
    const argsStr = Object.entries(args)
      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
      .join(', ');
    return `**${name}**(${argsStr})`;
  });
  return 'Approve the following action(s)?\n\n' + descriptions.join('\n');
}

/**
 * Processes common line types shared between chat and generate streams
 * @param {string} line - The line to process
 * @param {Object} res - The response object to write to
 * @returns {boolean} true if the line was handled, false otherwise
 */
function processCommonLineTypes(line, res) {
  if (line.startsWith('intermediate_data: ')) {
    processIntermediateData(line, res);
    return true;
  }
  if (line.startsWith('observability_trace: ')) {
    processObservabilityTrace(line, res);
    return true;
  }
  if (line.startsWith('thread_id: ')) {
    processThreadId(line, res);
    return true;
  }
  if (line.startsWith('interrupt: ')) {
    processInterrupt(line, res);
    return true;
  }
  if (line.trim().startsWith('{')) {
    res.write(line.trim());
    return true;
  }
  return false;
}

/**
 * Process any remaining buffer content after stream ends
 * Handles cases where error JSON doesn't have a trailing newline
 * @param {string} buffer - The remaining buffer content
 * @param {Object} res - The response object to write to
 */
function processRemainingBuffer(buffer, res) {
  const remaining = buffer.trim();
  if (remaining.startsWith('{')) {
    res.write(remaining);
  }
}

/**
 * Processes /chat/stream responses (SSE format)
 * Backend format: Stream with "data:" lines containing chat completion chunks
 * and "intermediate_data:" lines for progress updates
 */
async function processChatStream(backendRes, res) {
  if (!backendRes.ok) {
    res.writeHead(backendRes.status, { 'Content-Type': 'application/json' });
    res.end(await backendRes.text());
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Transfer-Encoding': 'chunked',
    'Access-Control-Allow-Origin': constants.CORS_ORIGIN,
    'Access-Control-Allow-Credentials': 'true',
  });

  const reader = backendRes.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]' || data === 'DONE') {
            res.end();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            const content =
              parsed.choices?.[0]?.message?.content ||
              parsed.choices?.[0]?.delta?.content;
            if (content) {
              res.write(content);
            }
          } catch (e) {
            // Ignore parse errors
          }
        } else {
          processCommonLineTypes(line, res);
        }
      }
    }

    processRemainingBuffer(buffer, res);
  } catch (err) {
    // Stream processing error
  } finally {
    res.end();
  }
}

/**
 * Processes /chat responses
 */
async function processChat(backendRes, res) {
  if (!backendRes.ok) {
    res.writeHead(backendRes.status, { 'Content-Type': 'application/json' });
    res.end(await backendRes.text());
    return;
  }

  const data = await backendRes.text();
  
  // Construct response headers
  const observabilityTraceId = backendRes.headers.get('observability-trace-id');
  const responseHeaders = {
    'Content-Type': 'text/plain; charset=utf-8',
    'Access-Control-Allow-Origin': constants.CORS_ORIGIN,
    'Access-Control-Allow-Credentials': 'true',
    ...(observabilityTraceId ? { 'Observability-Trace-Id': observabilityTraceId } : {}),
  };
  
  try {
    const parsed = JSON.parse(data);
    const content =
      parsed?.choices?.[0]?.message?.content ||
      parsed?.message ||
      parsed?.answer ||
      parsed?.value;

    res.writeHead(200, responseHeaders);
    res.end(typeof content === 'string' ? content : JSON.stringify(content));
  } catch (e) {
    res.writeHead(200, responseHeaders);
    res.end(data);
  }
}

/**
 * Processes /generate/stream endpoint responses (SSE format)
 */
async function processGenerateStream(backendRes, res) {
  if (!backendRes.ok) {
    res.writeHead(backendRes.status, { 'Content-Type': 'application/json' });
    res.end(await backendRes.text());
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Transfer-Encoding': 'chunked',
    'Access-Control-Allow-Origin': constants.CORS_ORIGIN,
    'Access-Control-Allow-Credentials': 'true',
  });

  const reader = backendRes.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]' || data === 'DONE') {
            res.end();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed?.value && typeof parsed.value === 'string') {
              res.write(data);
            }
          } catch (e) {
            // Ignore parse errors
          }
        } else {
          processCommonLineTypes(line, res);
        }
      }
    }

    processRemainingBuffer(buffer, res);
  } catch (err) {
    console.error('[ERROR] Stream processing error:', err.message);
  } finally {
    res.end();
  }
}

/**
 * Processes /generate endpoint responses
 */
async function processGenerate(backendRes, res) {
  if (!backendRes.ok) {
    res.writeHead(backendRes.status, { 'Content-Type': 'application/json' });
    res.end(await backendRes.text());
    return;
  }

  const data = await backendRes.text();

  // Construct response headers
  const observabilityTraceId = backendRes.headers.get('observability-trace-id');
  const responseHeaders = {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': constants.CORS_ORIGIN,
    'Access-Control-Allow-Credentials': 'true',
    ...(observabilityTraceId ? { 'Observability-Trace-Id': observabilityTraceId } : {}),
  };

  res.writeHead(200, responseHeaders);
  res.end(data);
}

/**
 * Processes Context-Aware RAG responses
 * Backend returns: {"status": "success", "result": "answer text"}
 * Also handles legacy formats: state.chat.answer, answer field
 */
async function processCaRag(backendRes, res) {
  if (!backendRes.ok) {
    res.writeHead(backendRes.status, { 'Content-Type': 'application/json' });
    res.end(await backendRes.text());
    return;
  }

  const data = await backendRes.text();
  try {
    const parsed = JSON.parse(data);
    const answer =
      parsed?.result ||
      parsed?.state?.chat?.answer ||
      parsed?.answer ||
      data;

    res.writeHead(200, {
      'Content-Type': 'text/plain; charset=utf-8',
      'Access-Control-Allow-Origin': constants.CORS_ORIGIN,
      'Access-Control-Allow-Credentials': 'true',
    });
    res.end(typeof answer === 'string' ? answer : JSON.stringify(answer));
  } catch (e) {
    res.writeHead(200, {
      'Content-Type': 'text/plain; charset=utf-8',
      'Access-Control-Allow-Origin': constants.CORS_ORIGIN,
      'Access-Control-Allow-Credentials': 'true',
    });
    res.end(data);
  }
}

module.exports = {
  processChatStream,
  processChat,
  processGenerateStream,
  processGenerate,
  processCaRag,
};
