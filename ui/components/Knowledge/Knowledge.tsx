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

import { useState, useEffect, useMemo } from 'react';
import {
  IconBook,
  IconFileText,
  IconSearch,
  IconRefresh,
  IconFolder,
  IconFolderOpen,
  IconSettings,
  IconBrain,
  IconHistory,
  IconSortDescending,
  IconSortAscending,
} from '@tabler/icons-react';

import remarkGfm from 'remark-gfm';
import { getReactMarkDownCustomComponents } from '../Markdown/CustomComponents';
import { MemoizedReactMarkdown } from '../Markdown/MemoizedReactMarkdown';

interface KnowledgeDocument {
  id: string;
  title: string;
  filename: string;
  folder: string | null;
  description: string;
  size: number;
  modified: number;
}

interface KnowledgeData {
  documents: KnowledgeDocument[];
  folders: {
    documents: KnowledgeDocument[];
    skills: KnowledgeDocument[];
    memory: KnowledgeDocument[];
  };
  system_prompt: string;
  count: number;
}

interface KnowledgeDocumentContent {
  id: string;
  title: string;
  filename: string;
  content: string;
  size: number;
}

type SortOrder = 'newest' | 'oldest' | 'name';

export const Knowledge = () => {
  // State management
  const [data, setData] = useState<KnowledgeData | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocumentContent | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Folder expansion state
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    documents: true,
    skills: true,
    memory: true,
  });

  // Sort order
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');

  const markdownComponents = useMemo(
    () => getReactMarkDownCustomComponents(),
    [],
  );

  // Skill docs (and some knowledge files) open with a YAML frontmatter block
  // (`---\n...\n---`). react-markdown would render it as a horizontal rule
  // plus raw key/value lines; rewrite it into a fenced yaml code block so
  // the CodeBlock component can highlight it.
  const renderedContent = useMemo(() => {
    const raw = selectedDocument?.content ?? '';
    return raw.replace(
      /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/,
      (_m, body) => '```yaml\n' + body + '\n```\n\n',
    );
  }, [selectedDocument?.content]);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/knowledge/list?include_system=true');
      if (!response.ok) {
        throw new Error(`Failed to load documents: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      setData(result);
      setLastUpdated(new Date());

      // Auto-select first document if available and none selected
      if (!selectedDocument) {
        if (result.documents?.length > 0) {
          await loadDocumentContent(result.documents[0].id);
        } else if (result.folders?.skills?.length > 0) {
          await loadDocumentContent(result.folders.skills[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load knowledge documents:', err);
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const loadDocumentContent = async (documentId: string) => {
    try {
      setLoadingContent(true);
      setError(null);

      const response = await fetch(`/api/knowledge/read/${documentId}`);
      if (!response.ok) {
        throw new Error(`Failed to load document: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      setSelectedDocument(result);
    } catch (err) {
      console.error('Failed to load document content:', err);
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoadingContent(false);
    }
  };

  const toggleFolder = (folderName: string) => {
    setExpandedFolders(prev => ({
      ...prev,
      [folderName]: !prev[folderName],
    }));
  };

  const cycleSortOrder = () => {
    setSortOrder(prev => {
      if (prev === 'newest') return 'oldest';
      if (prev === 'oldest') return 'name';
      return 'newest';
    });
  };

  // Sort documents
  const sortDocs = (docs: KnowledgeDocument[]) => {
    return [...docs].sort((a, b) => {
      if (sortOrder === 'newest') return b.modified - a.modified;
      if (sortOrder === 'oldest') return a.modified - b.modified;
      return a.title.localeCompare(b.title);
    });
  };

  // Filter documents based on search
  const filterDocs = (docs: KnowledgeDocument[]) => {
    if (!searchQuery.trim()) return docs;
    const query = searchQuery.toLowerCase();
    return docs.filter(
      (doc) =>
        doc.title.toLowerCase().includes(query) ||
        doc.description.toLowerCase().includes(query)
    );
  };

  // Format file size
  const formatSize = (bytes: number | undefined) => {
    if (bytes === undefined || bytes === null || isNaN(bytes)) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Format date
  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  const totalCount = data
    ? data.documents.length +
      (data.folders?.documents?.length || 0) +
      (data.folders?.skills?.length || 0) +
      (data.folders?.memory?.length || 0)
    : 0;

  if (loading && !data) {
    return (
      <div className="flex flex-col h-full bg-white dark:bg-[#343541] pt-3">
        <div className="h-full flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">
              Loading knowledge base...
            </p>
          </div>
        </div>
      </div>
    );
  }

  const renderDocumentItem = (doc: KnowledgeDocument, isSystemPrompt = false) => (
    <div
      key={doc.id}
      className={`flex items-start gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
        selectedDocument?.id === doc.id
          ? 'bg-blue-100 dark:bg-blue-900/30 border-l-4 border-blue-500'
          : 'hover:bg-gray-100 dark:hover:bg-gray-800'
      }`}
      onClick={() => loadDocumentContent(doc.id)}
    >
      {isSystemPrompt ? (
        <IconSettings size={16} className="text-purple-400 flex-shrink-0 mt-0.5" />
      ) : (
        <IconFileText size={16} className="text-blue-400 flex-shrink-0 mt-0.5" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
          {doc.title}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {formatDate(doc.modified)}{formatSize(doc.size) && ` · ${formatSize(doc.size)}`}
        </p>
      </div>
    </div>
  );

  const renderFolder = (
    name: string,
    icon: React.ReactNode,
    docs: KnowledgeDocument[],
    emptyMessage: string
  ) => {
    const isExpanded = expandedFolders[name];
    const filteredDocs = filterDocs(sortDocs(docs));

    return (
      <div key={name} className="mb-2">
        <div
          className="flex items-center gap-2 px-2 py-1.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          onClick={() => toggleFolder(name)}
        >
          {isExpanded ? (
            <IconFolderOpen size={16} className="text-yellow-500" />
          ) : (
            <IconFolder size={16} className="text-yellow-500" />
          )}
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
            {name}
          </span>
          <span className="text-xs text-gray-400 ml-auto">
            {docs.length}
          </span>
        </div>
        {isExpanded && (
          <div className="ml-4 mt-1 space-y-0.5">
            {filteredDocs.length === 0 ? (
              <p className="text-xs text-gray-400 italic px-3 py-2">
                {emptyMessage}
              </p>
            ) : (
              filteredDocs.map((doc) => renderDocumentItem(doc))
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#343541] pt-3">
      {/* Header */}
      <div className="bg-white dark:bg-[#202123] border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <IconBook className="text-blue-500" size={28} />
            <div>
              <h1 className="text-xl font-bold text-gray-800 dark:text-gray-100">
                Knowledge Base
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Quantum calibration documentation and guides
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={loadDocuments}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors ${
                loading
                  ? 'bg-gray-100 dark:bg-gray-800 cursor-not-allowed'
                  : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
              title="Refresh"
            >
              <IconRefresh
                size={18}
                className={`text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Document Tree */}
        <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-[#202123] flex flex-col">
          {error && (
            <div className="m-2 p-2 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded">
              <p className="text-red-700 dark:text-red-300 text-xs">{error}</p>
            </div>
          )}

          {/* Search & Sort */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <IconSearch
                  size={14}
                  className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-gray-400"
                />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-2 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={cycleSortOrder}
                className="p-1.5 border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
                title={`Sort: ${sortOrder}`}
              >
                {sortOrder === 'newest' ? (
                  <IconSortDescending size={16} className="text-gray-600 dark:text-gray-400" />
                ) : sortOrder === 'oldest' ? (
                  <IconSortAscending size={16} className="text-gray-600 dark:text-gray-400" />
                ) : (
                  <IconSortDescending size={16} className="text-gray-400" />
                )}
              </button>
            </div>
            <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
              {totalCount} documents · {sortOrder === 'newest' ? 'Newest first' : sortOrder === 'oldest' ? 'Oldest first' : 'By name'}
            </p>
          </div>

          {/* Document Tree */}
          <div className="flex-1 overflow-y-auto p-2">
            {/* System Prompt */}
            {data?.system_prompt && (
              <div className="mb-3">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase px-2 mb-1">
                  System
                </p>
                {renderDocumentItem(
                  {
                    id: data.system_prompt,
                    title: 'System Prompt',
                    filename: `${data.system_prompt}.md`,
                    folder: null,
                    description: 'Agent system prompt configuration',
                    size: 0,
                    modified: Date.now() / 1000,
                  },
                  true
                )}
              </div>
            )}

            {/* Documents Folder */}
            {data?.folders?.documents && (
              renderFolder(
                'documents',
                <IconFileText size={16} />,
                data.folders.documents,
                'No documentation yet'
              )
            )}

            {/* Skills Folder */}
            {data?.folders?.skills && (
              renderFolder(
                'skills',
                <IconBrain size={16} />,
                data.folders.skills,
                'No skills documented yet'
              )
            )}

            {/* Memory Folder */}
            {data?.folders?.memory && (
              renderFolder(
                'memory',
                <IconHistory size={16} />,
                data.folders.memory,
                'No memories recorded yet'
              )
            )}

            {/* Root Documents (system prompt only now) */}
            {data?.documents && data.documents.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase px-2 mb-1">
                  System
                </p>
                <div className="space-y-0.5">
                  {filterDocs(sortDocs(data.documents)).map((doc) =>
                    renderDocumentItem(doc)
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Document Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {loadingContent ? (
            <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-[#343541]">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">
                  Loading document...
                </p>
              </div>
            </div>
          ) : selectedDocument ? (
            <>
              {/* Document Header */}
              <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-[#202123]">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                  {selectedDocument.title}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {selectedDocument.filename}{formatSize(selectedDocument.size) && ` · ${formatSize(selectedDocument.size)}`}
                </p>
              </div>

              {/* Document Content */}
              <div className="flex-1 overflow-y-auto bg-white dark:bg-[#343541]">
                <div className="p-6 max-w-4xl mx-auto">
                  <div className="prose dark:prose-invert max-w-none prose-pre:bg-gray-100 dark:prose-pre:bg-gray-800 prose-code:text-blue-600 dark:prose-code:text-blue-400">
                    <MemoizedReactMarkdown
                      className="markdown"
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {renderedContent}
                    </MemoizedReactMarkdown>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-[#343541]">
              <div className="text-center">
                <IconBook className="mx-auto text-gray-400 mb-4" size={48} />
                <p className="text-gray-500 dark:text-gray-400">
                  Select a document from the sidebar to view
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
