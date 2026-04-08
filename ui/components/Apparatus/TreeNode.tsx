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

import React from 'react';
import { IconChevronRight, IconChevronDown, IconFile, IconFolder, IconFolderOpen } from '@tabler/icons-react';

interface TreeNodeData {
  [key: string]: TreeNodeData | null;
}

interface TreeNodeProps {
  name: string;
  path: string;
  childNodes?: TreeNodeData | null;
  expandedNodes: Set<string>;
  selectedPath: string | null;
  level?: number;
  onToggle?: (path: string) => void;
  onSelect?: (path: string) => void;
}

export const TreeNode: React.FC<TreeNodeProps> = ({
  name,
  path,
  childNodes,
  expandedNodes,
  selectedPath,
  level = 0,
  onToggle,
  onSelect
}) => {
  const hasChildren = childNodes && typeof childNodes === 'object' && Object.keys(childNodes).length > 0;
  const isExpanded = expandedNodes.has(path);
  const isSelected = selectedPath === path;
  const indent = level * 20;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasChildren && onToggle) {
      onToggle(path);
    } else if (onSelect) {
      onSelect(path);
    }
  };

  return (
    <div>
      <div
        className={`flex items-center py-1.5 px-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
          isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500' : ''
        }`}
        style={{ paddingLeft: `${indent + 8}px` }}
        onClick={handleClick}
      >
        {hasChildren ? (
          <>
            <span className="mr-1">
              {isExpanded ? (
                <IconChevronDown size={16} className="text-gray-500" />
              ) : (
                <IconChevronRight size={16} className="text-gray-500" />
              )}
            </span>
            <span className="mr-2">
              {isExpanded ? (
                <IconFolderOpen size={16} className="text-blue-500" />
              ) : (
                <IconFolder size={16} className="text-blue-500" />
              )}
            </span>
          </>
        ) : (
          <>
            <span className="mr-1 invisible">
              <IconChevronRight size={16} />
            </span>
            <span className="mr-2">
              <IconFile size={16} className="text-gray-400" />
            </span>
          </>
        )}
        <span
          className={`text-sm ${!hasChildren ? 'cursor-pointer hover:text-blue-600 dark:hover:text-blue-400' : ''} ${
            isSelected ? 'font-medium text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'
          }`}
          onClick={(e) => {
            e.stopPropagation();
            if (!hasChildren && onSelect) {
              onSelect(path);
            }
          }}
        >
          {name}
        </span>
      </div>

      {hasChildren && isExpanded && childNodes && (
        <div>
          {Object.entries(childNodes).map(([childName, childValue]) => (
            <TreeNode
              key={`${path}.${childName}`}
              name={childName}
              path={`${path}.${childName}`}
              childNodes={childValue}
              expandedNodes={expandedNodes}
              selectedPath={selectedPath}
              level={level + 1}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};
