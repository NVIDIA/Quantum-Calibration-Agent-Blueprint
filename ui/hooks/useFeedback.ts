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

import { useCallback } from 'react';
import toast from 'react-hot-toast';

type FeedbackPayload = {
  observability_trace_id: string;
  reaction_type?: '👍' | '👎';
  comment?: string;
};

export const useFeedback = () => {
  const submitFeedback = useCallback(async (
    traceId: string,
    reactionType?: '👍' | '👎',
    comment?: string
  ) => {
    try {
      const payload: FeedbackPayload = {
        observability_trace_id: traceId,
      };

      if (reactionType) {
        payload.reaction_type = reactionType;
      }

      if (comment) {
        payload.comment = comment;
      }

      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await response.json();
      
      if (reactionType) {
        toast(`Feedback submitted successfully`, {icon: reactionType});
      } else if (comment) {
        toast.success('Feedback comment submitted successfully');
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      toast.error('Failed to submit feedback');
      throw error;
    }
  }, []);

  return {
    submitFeedback
  };
};
