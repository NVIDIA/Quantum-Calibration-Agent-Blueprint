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

import {
  saveConversation,
  saveConversations,
  updateConversation,
} from '@/utils/app/conversation';

import { v4 as uuidv4 } from 'uuid';

export const useConversationOperations = ({
  conversations,
  dispatch,
  t,
  appConfig,
}) => {
  const handleSelectConversation = (conversation) => {
    // Clear any streaming states before switching conversations
    dispatch({ field: 'messageIsStreaming', value: false });
    dispatch({ field: 'loading', value: false });

    dispatch({
      field: 'selectedConversation',
      value: conversation,
    });

    // updating the session id based on the selcted conversation
    sessionStorage.setItem('sessionId', conversation?.id);
    saveConversation(conversation);
  };

  const handleNewConversation = () => {
    const lastConversation = conversations[conversations.length - 1];

    const newConversation = {
      id: uuidv4(),
      name: t('New Conversation'),
      messages: [],
      folderId: null,
    };

    // setting new the session id for new chat conversation
    sessionStorage.setItem('sessionId', newConversation.id);
    const updatedConversations = [...conversations, newConversation];

    dispatch({ field: 'selectedConversation', value: newConversation });
    dispatch({ field: 'conversations', value: updatedConversations });

    saveConversations(updatedConversations);

    dispatch({ field: 'loading', value: false });
  };

  const handleUpdateConversation = (conversation, data) => {
    const updatedConversation = {
      ...conversation,
      [data.key]: data.value,
    };

    const { single, all } = updateConversation(
      updatedConversation,
      conversations,
    );

    dispatch({ field: 'selectedConversation', value: single });
    dispatch({ field: 'conversations', value: all });

    saveConversations(all);
  };

  return {
    handleSelectConversation,
    handleNewConversation,
    handleUpdateConversation,
  };
};
