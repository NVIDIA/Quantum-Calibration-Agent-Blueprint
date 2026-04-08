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

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  IconX,
  IconCopy,
  IconCheck,
  IconFileText,
  IconLoader2,
  IconCode
} from '@tabler/icons-react';

// Dynamic import to avoid ESM issues
const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter/dist/esm/prism-light').then(mod => mod.default),
  { ssr: false }
);

// Import style separately
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeViewerProps {
  experimentName: string | null;
  modulePath?: string;
  onClose: () => void;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  experimentName,
  modulePath,
  onClose
}) => {
  const [content, setContent] = useState<string | null>(null);
  const [loadingSource, setLoadingSource] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let isActive = true;

    if (!experimentName) {
      setContent(null);
      setSourceError(null);
      return () => { isActive = false; };
    }

    const fetchScript = async () => {
      setLoadingSource(true);
      setSourceError(null);

      try {
        const response = await fetch(`/api/experiment/script/${encodeURIComponent(experimentName)}`);
        const result = await response.json();

        if (!isActive) return;

        if (result.content) {
          setContent(result.content);
        } else {
          setSourceError(result.error || 'Failed to load script');
          setContent(null);
        }
      } catch (err) {
        if (!isActive) return;
        setSourceError(err instanceof Error ? err.message : 'Failed to load script');
        setContent(null);
      } finally {
        if (isActive) {
          setLoadingSource(false);
        }
      }
    };

    fetchScript();

    return () => {
      isActive = false;
    };
  }, [experimentName]);

  const handleCopy = async () => {
    if (!content) return;

    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Silently ignore copy failures
    }
  };

  const filename = modulePath ? modulePath.split('/').pop() : 'script.py';

  if (!experimentName) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900 text-gray-400">
        <div className="text-center">
          <IconFileText size={48} className="mx-auto mb-4 opacity-50" />
          <p>Select an experiment to view its source code</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <IconCode size={16} className="text-gray-400" />
          <span className="font-mono text-sm text-gray-400 truncate" title={modulePath}>
            {filename}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            disabled={!content || copied}
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Copy script content"
          >
            {copied ? (
              <>
                <IconCheck size={16} className="text-green-400" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <IconCopy size={16} />
                <span>Copy</span>
              </>
            )}
          </button>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Close viewer"
          >
            <IconX size={18} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {loadingSource ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <IconLoader2 size={32} className="mx-auto mb-2 animate-spin" />
              <p>Loading script...</p>
            </div>
          </div>
        ) : sourceError ? (
          <div className="h-full flex items-center justify-center text-red-400 p-4">
            <div className="text-center">
              <IconFileText size={32} className="mx-auto mb-2 opacity-50" />
              <p className="font-medium">Failed to load script</p>
              <p className="text-sm mt-1 text-gray-500">{sourceError}</p>
            </div>
          </div>
        ) : content ? (
          <SyntaxHighlighter
            language="python"
            style={atomDark}
            showLineNumbers
            wrapLines
            customStyle={{
              margin: 0,
              padding: '1rem',
              background: 'transparent',
              fontSize: '13px',
              minHeight: '100%'
            }}
            lineNumberStyle={{
              minWidth: '3em',
              paddingRight: '1em',
              color: '#6b7280',
              userSelect: 'none'
            }}
          >
            {content}
          </SyntaxHighlighter>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500">
            <p>No content available</p>
          </div>
        )}
      </div>
    </div>
  );
};
