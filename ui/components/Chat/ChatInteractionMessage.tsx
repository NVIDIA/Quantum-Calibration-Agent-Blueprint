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

'use client';
import { IconInfoCircle, IconX } from '@tabler/icons-react';
import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { MemoizedReactMarkdown } from '@/components/Markdown/MemoizedReactMarkdown';

const WARNING_THRESHOLD = 0.2; // Show red warning when 20% of time remains

interface InteractionContent {
  input_type?: string;
  text?: string;
  placeholder?: string;
  required?: boolean;
  timeout?: number | null;
  error?: string | null;
  options?: Array<{ id: string; label: string; value: string }>;
}

interface InteractionMessage {
  id?: string;
  content?: InteractionContent;
}

interface InteractionModalProps {
  isOpen: boolean;
  interactionMessage: InteractionMessage | null;
  onClose: () => void;
  onSubmit: (data: { interactionMessage: InteractionMessage; userResponse: string }) => void;
}

export const InteractionModal = ({
  isOpen,
  interactionMessage,
  onClose,
  onSubmit,
}: InteractionModalProps) => {
  const { content } = interactionMessage || {};
  const [userInput, setUserInput] = useState('');
  const [error, setError] = useState('');
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [isTimedOut, setIsTimedOut] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const clearTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  useEffect(() => {
    if (!isOpen || !interactionMessage) return;
    
    const timeout = content?.timeout;
    if (typeof timeout === 'number' && timeout > 0) {
      setRemainingSeconds(timeout);
      setIsTimedOut(false);
      
      intervalRef.current = setInterval(() => {
        setRemainingSeconds((prev) => {
          if (prev === null || prev <= 1) {
            clearTimer();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      setRemainingSeconds(null);
    }

    return () => clearTimer();
  }, [isOpen, interactionMessage?.id]);

  useEffect(() => {
    if (remainingSeconds === 0 && !isTimedOut) {
      setIsTimedOut(true);
      toast.error(content?.error || 'This prompt is no longer available.');
      onClose();
    }
  }, [remainingSeconds, isTimedOut, content?.error, onClose]);

  useEffect(() => {
    if (!isOpen) {
      setUserInput('');
      setError('');
      setRemainingSeconds(null);
      setIsTimedOut(false);
      clearTimer();
    }
  }, [isOpen]);

  if (!isOpen || !interactionMessage) return null;

  const submitResponse = (response: string) => {
    if (isTimedOut) return false;
    setError('');
    clearTimer();
    onSubmit({ interactionMessage, userResponse: response });
    onClose();
    return true;
  };

  const handleTextSubmit = () => {
    if (content?.required && !userInput.trim()) {
      setError('This field is required.');
      return;
    }
    submitResponse(userInput);
  };

  const handleChoiceSubmit = (option = '') => {
    if (content?.required && !option) {
      setError('Please select an option.');
      return;
    }
    submitResponse(option);
  };

  const handleRadioSubmit = () => {
    if (content?.required && !userInput) {
      setError('Please select an option.');
      return;
    }
    submitResponse(userInput);
  };

  if (content?.input_type === 'notification') {
    toast.custom(
      (t) => (
        <div
          className={`flex gap-2 items-center justify-evenly bg-white text-slate-800 dark:bg-slate-800 dark:text-slate-100 px-4 py-2 rounded-lg shadow-md ${
            t.visible ? 'animate-fade-in' : 'animate-fade-out'
          }`}
        >
          <IconInfoCircle size={16} className="text-[#76b900]" />
          <span>
            {content?.text || 'No content found for this notification'}
          </span>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="text-slate-800 dark:bg-slate-800 dark:text-slate-100 ml-3 hover:bg-slate-300 rounded-full p-1"
          >
            <IconX size={12} />
          </button>
        </div>
      ),
      {
        position: 'top-right',
        duration: Infinity,
        id: 'notification-toast',
      },
    );
    return null;
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
      <div className="bg-white dark:bg-zinc-800 p-6 rounded-lg shadow-lg sm:w-[75%] md:w-1/3 h-auto border dark:border-zinc-600">
        <div className="mb-4 text-slate-800 dark:text-slate-100">
          <MemoizedReactMarkdown
            className="prose dark:prose-invert prose-sm max-w-none"
          >
            {content?.text || ''}
          </MemoizedReactMarkdown>
        </div>

        {remainingSeconds !== null && (
          <p className={`text-sm mb-3 ${remainingSeconds <= (content?.timeout || 0) * WARNING_THRESHOLD ? 'text-red-500 font-semibold' : 'text-slate-500 dark:text-slate-400'}`}>
            Time remaining: {formatTime(remainingSeconds)}
          </p>
        )}

        {content?.input_type === 'text' && (
          <div>
            <textarea
              className="w-full border dark:border-zinc-600 p-2 rounded text-slate-800 dark:text-slate-100 bg-white dark:bg-zinc-700 disabled:bg-gray-100 dark:disabled:bg-zinc-600 disabled:cursor-not-allowed"
              placeholder={content?.placeholder}
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              disabled={isTimedOut}
            />
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
            <div className="flex justify-end mt-4">
              <button
                className="px-4 py-2 bg-[#76b900] text-white rounded disabled:bg-gray-400 disabled:cursor-not-allowed"
                onClick={handleTextSubmit}
                disabled={isTimedOut}
              >
                Submit
              </button>
            </div>
          </div>
        )}

        {content?.input_type === 'binary_choice' && (
          <div>
            <div className="flex justify-end mt-4 space-x-2">
              {content?.options?.map((option) => (
                <button
                  key={option.id}
                  className={`px-4 py-2 ${
                    option?.value?.includes('continue')
                      ? 'bg-[#76b900]'
                      : 'bg-slate-800'
                  } text-white rounded disabled:bg-gray-400 disabled:cursor-not-allowed`}
                  onClick={() => handleChoiceSubmit(option.value)}
                  disabled={isTimedOut}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {content?.input_type === 'radio' && (
          <div>
            <div className="space-y-3">
              {content?.options?.map((option) => (
                <div key={option.id} className="flex items-center">
                  <input
                    type="radio"
                    id={option.id}
                    name="notification-method"
                    value={option.value}
                    checked={userInput === option.value}
                    onChange={() => setUserInput(option.value)}
                    className="mr-2 text-[#76b900] focus:ring-[#76b900] disabled:cursor-not-allowed"
                    disabled={isTimedOut}
                  />
                  <label htmlFor={option.id} className="flex flex-col">
                    <span className="text-slate-800 dark:text-slate-100">
                      {option.label}
                    </span>
                  </label>
                </div>
              ))}
            </div>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
            <div className="flex justify-end mt-4">
              <button
                className="px-4 py-2 bg-[#76b900] text-white rounded disabled:bg-gray-400 disabled:cursor-not-allowed"
                onClick={handleRadioSubmit}
                disabled={isTimedOut}
              >
                Submit
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
