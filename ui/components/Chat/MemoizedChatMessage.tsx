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

import { ChatMessage, Props } from './ChatMessage';

import isEqual from 'lodash/isEqual';

export const MemoizedChatMessage: FC<Props> = memo(
  ChatMessage,
  (prevProps, nextProps) => {
    // Component should NOT re-render if all props are the same
    const messageEqual = isEqual(prevProps.message, nextProps.message);
    const messageIndexEqual = prevProps.messageIndex === nextProps.messageIndex;
    const onEditEqual = prevProps.onEdit === nextProps.onEdit;

    // Return true if all props are equal (don't re-render)
    return messageEqual && messageIndexEqual && onEditEqual;
  },
);
