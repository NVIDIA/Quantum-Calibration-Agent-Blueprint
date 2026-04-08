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

import { FC, memo } from 'react';
import ReactMarkdown, { Options, defaultUrlTransform } from 'react-markdown';

type MemoizedOptions = Options & { className?: string };

/**
 * Custom URL transform that allows data: URIs for inline base64 images
 * while using the default transform for all other URLs
 */
const customUrlTransform = (url: string): string => {
  // Allow data: URIs (base64 encoded images) to pass through unchanged
  if (url.startsWith('data:')) {
    return url;
  }
  // Use default transform for all other URLs
  return defaultUrlTransform(url);
};

export const MemoizedReactMarkdown: FC<MemoizedOptions> = memo(
  ({ className, children, urlTransform = customUrlTransform, ...rest }) => (
    <div className={className}>
      <ReactMarkdown urlTransform={urlTransform} {...rest}>{children}</ReactMarkdown>
    </div>
  ),
  (prevProps, nextProps) =>
    prevProps.children === nextProps.children &&
    prevProps.className === nextProps.className,
);
