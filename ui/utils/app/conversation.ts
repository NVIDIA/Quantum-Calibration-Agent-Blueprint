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

import toast from 'react-hot-toast';

import { Conversation, Role } from '@/types/chat';

export const updateConversation = (
  updatedConversation: Conversation,
  allConversations: Conversation[],
) => {
  const updatedConversations = allConversations.map((c) => {
    if (c.id === updatedConversation.id) {
      return updatedConversation;
    }

    return c;
  });

  saveConversation(updatedConversation);
  saveConversations(updatedConversations);

  return {
    single: updatedConversation,
    all: updatedConversations,
  };
};

export const saveConversation = (conversation: Conversation) => {
  try {
    sessionStorage.setItem(
      'selectedConversation',
      JSON.stringify(conversation),
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.log('Storage quota exceeded, cannot save conversation.');
      toast.error('Storage quota exceeded, cannot save conversation.');
    }
  }
};

export const saveConversations = (conversations: Conversation[]) => {
  try {
    sessionStorage.setItem(
      'conversationHistory',
      JSON.stringify(conversations),
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.log('Storage quota exceeded, cannot save conversations.');
      toast.error('Storage quota exceeded, cannot save conversation.');
    }
  }
};
