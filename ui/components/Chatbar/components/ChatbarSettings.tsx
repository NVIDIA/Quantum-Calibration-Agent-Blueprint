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

import { useContext } from 'react';

import HomeContext from '@/pages/api/home/home.context';

import ChatbarContext from '../Chatbar.context';
import { ClearConversations } from './ClearConversations';
import { ModeSelector } from './ModeSelector';

export const ChatbarSettings = () => {
  const {
    state: { conversations },
  } = useContext(HomeContext);

  const { handleClearConversations } = useContext(ChatbarContext);

  return (
    <div className="flex flex-col">
      <div className="flex flex-col items-center space-y-1 border-t border-white/20 pt-1 text-sm">
        {conversations.length > 0 ? (
          <ClearConversations onClearConversations={handleClearConversations} />
        ) : null}
      </div>
      <ModeSelector />
    </div>
  );
};
