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
 * Response processors for LangGraph API server
 * Transforms LangGraph SSE format to NAT UI format
 */

const constants = require('../constants');

/**
 * Process LangGraph /runs/stream SSE response
 *
 * LangGraph format:
 *   event: metadata
 *   data: {"run_id": "..."}
 *
 *   event: messages/partial
 *   data: [{"content": [{"text": "Hello", "type": "text"}], "type": "ai"}]
 *
 *   event: values
 *   data: {"messages": [...]}
 *
 *   event: updates
 *   data: {"node_name": {...}}
 *
 *   event: end
 *   data: null
 */
async function processLangGraphStream(backendRes, res) {
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
  let lastContentLength = 0; // Track content length to compute delta
  let runId = null;
  let stepCounter = 0;

  // Track emitted tool calls to avoid duplicates
  // Key: tool_call_id or index, Value: step_id
  const emittedToolCalls = new Map();

  // Track emitted tool results
  const emittedToolResults = new Set();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = null;

      for (const line of lines) {
        // Parse SSE event type
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
          continue;
        }

        // Parse SSE data
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          if (!dataStr || dataStr === 'null') continue;

          try {
            const data = JSON.parse(dataStr);

            switch (currentEvent) {
              case 'metadata':
                // Extract run_id as thread_id
                if (data.run_id) {
                  runId = data.run_id;
                  res.write(`<threadid>${runId}</threadid>`);
                }
                break;

              case 'messages/partial':
                // Handle streaming messages - this is where tokens come in
                // Format: [{"content": [{"text": "...", "type": "text"}], "type": "ai", ...}]
                if (Array.isArray(data) && data.length > 0) {
                  const message = data[0];
                  if (message.type === 'ai' && message.content) {
                    // Content can be array of blocks or string
                    let fullContent = '';
                    if (Array.isArray(message.content)) {
                      for (const block of message.content) {
                        if (block.type === 'text' && block.text) {
                          fullContent += block.text;
                        }
                      }
                    } else if (typeof message.content === 'string') {
                      fullContent = message.content;
                    }

                    // Compute delta (new content since last update)
                    if (fullContent.length > lastContentLength) {
                      const delta = fullContent.slice(lastContentLength);
                      res.write(delta);
                      lastContentLength = fullContent.length;
                    }

                    // Handle tool calls - deduplicate by ID
                    if (message.tool_calls && message.tool_calls.length > 0) {
                      for (let i = 0; i < message.tool_calls.length; i++) {
                        const tc = message.tool_calls[i];
                        // Use tool call ID or index as key
                        const tcKey = tc.id || `idx_${i}`;

                        // Skip if already emitted
                        if (emittedToolCalls.has(tcKey)) {
                          continue;
                        }

                        stepCounter++;
                        const stepId = `step_${stepCounter}`;
                        emittedToolCalls.set(tcKey, stepId);

                        const step = {
                          id: stepId,
                          status: 'in_progress',
                          type: 'system_intermediate',
                          content: {
                            name: `🔧 ${tc.name || 'Tool'}`,
                            payload: tc.args
                              ? `**Args:** \`${JSON.stringify(tc.args)}\``
                              : 'Executing...',
                          },
                        };
                        res.write(
                          `<intermediatestep>${JSON.stringify(step)}</intermediatestep>`
                        );
                      }
                    }
                  }
                }
                break;

              case 'values':
                // Values events contain full state - can be used for final content
                // We primarily rely on messages/partial for streaming
                break;

              case 'updates':
                // Extract tool calls and node updates as intermediate steps
                for (const [nodeName, nodeData] of Object.entries(data)) {
                  if (nodeName === '__interrupt__') {
                    // Handle HITL interrupt
                    const interrupt = Array.isArray(nodeData)
                      ? nodeData[0]
                      : nodeData;
                    const interruptValue = interrupt?.value || interrupt;
                    const interruptId =
                      interrupt?.id || `interrupt_${Date.now()}`;

                    const actions = (
                      interruptValue?.action_requests || []
                    ).map((a) => ({
                      name: a.name || 'unknown',
                      args: a.args || {},
                      description: a.description || '',
                    }));

                    const interactionMessage = {
                      type: 'system_interaction_message',
                      id: interruptId,
                      thread_id: runId,
                      content: {
                        input_type: 'binary_choice',
                        text: formatInterruptText(actions),
                        options: [
                          { id: 'approve', label: 'Approve', value: 'approve' },
                          { id: 'reject', label: 'Reject', value: 'reject' },
                        ],
                        timeout: 300,
                      },
                    };
                    res.write(
                      `<systeminteraction>${JSON.stringify(interactionMessage)}</systeminteraction>`
                    );
                    continue;
                  }

                  // Skip null updates and metadata nodes
                  if (nodeData === null) continue;
                  if (nodeName.includes('Middleware')) continue;

                  // Tool node updates - check for tool messages (results)
                  if (nodeData?.messages) {
                    const messages = Array.isArray(nodeData.messages)
                      ? nodeData.messages
                      : [nodeData.messages];

                    for (const msg of messages) {
                      if (msg.type === 'tool') {
                        // Use tool_call_id to find the original step and mark as complete
                        const toolCallId = msg.tool_call_id;
                        const resultKey = toolCallId || msg.id || `result_${stepCounter}`;

                        // Skip if already emitted this result
                        if (emittedToolResults.has(resultKey)) {
                          continue;
                        }
                        emittedToolResults.add(resultKey);

                        // Check if we have a matching step to update
                        let stepId;
                        if (toolCallId && emittedToolCalls.has(toolCallId)) {
                          stepId = emittedToolCalls.get(toolCallId);
                        } else {
                          stepCounter++;
                          stepId = `step_${stepCounter}`;
                        }

                        const step = {
                          id: stepId,
                          status: 'complete',
                          type: 'system_intermediate',
                          content: {
                            name: `🔧 ${msg.name || 'Tool'} Result`,
                            payload: truncate(
                              typeof msg.content === 'string'
                                ? msg.content
                                : JSON.stringify(msg.content),
                              500
                            ),
                          },
                        };
                        res.write(
                          `<intermediatestep>${JSON.stringify(step)}</intermediatestep>`
                        );
                      }
                    }
                  }
                }
                break;

              case 'messages/metadata':
                // Metadata about messages - skip
                break;

              case 'end':
                // Stream complete
                break;
            }
          } catch (e) {
            // Ignore parse errors
            console.error('[LangGraph] Parse error:', e.message);
          }
          currentEvent = null;
        }
      }
    }
  } catch (err) {
    console.error('[LangGraph] Stream error:', err.message);
  } finally {
    res.end();
  }
}

/**
 * Format interrupt actions into readable text
 */
function formatInterruptText(actions) {
  if (!actions || actions.length === 0) {
    return 'Approve pending action?';
  }
  const descriptions = actions.map((action) => {
    const name = action.name || 'unknown';
    const desc = action.description || '';
    if (desc) return `**${name}**: ${desc}`;
    const argsStr = Object.entries(action.args || {})
      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
      .join(', ');
    return `**${name}**(${argsStr})`;
  });
  return 'Approve the following action(s)?\n\n' + descriptions.join('\n');
}

/**
 * Truncate string to max length
 */
function truncate(str, max) {
  if (!str) return '';
  const s = String(str);
  return s.length > max ? s.slice(0, max) + '...' : s;
}

/**
 * Transform NAT UI chat request to LangGraph format
 */
function transformChatRequest(body, assistantId = 'agent') {
  const parsed = JSON.parse(body);

  // NAT UI sends: { messages: [{role: "user", content: "..."}] }
  // LangGraph expects: { input: { messages: [...] } }

  const messages = (parsed.messages || []).map((m) => ({
    type:
      m.role === 'user' ? 'human' : m.role === 'assistant' ? 'ai' : 'system',
    content: m.content,
  }));

  return JSON.stringify({
    assistant_id: assistantId,
    thread_id: parsed.thread_id || null, // null = stateless
    input: { messages },
    stream_mode: ['values', 'updates', 'messages'],
    stream_subgraphs: true,
  });
}

module.exports = {
  processLangGraphStream,
  transformChatRequest,
};
