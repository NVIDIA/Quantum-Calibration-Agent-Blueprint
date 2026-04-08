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

import { useState, useEffect, useRef } from 'react';

/**
 * Hook that gradually reveals text character-by-character for a typewriter effect.
 *
 * @param targetText - The full text to reveal
 * @param isActive - Whether the typewriter effect should be active (typically messageIsStreaming && isLastMessage)
 * @param charsPerFrame - Number of characters to reveal per animation frame (default: 3)
 * @returns { displayedText, isRevealing, cursorVisible }
 */
export function useTypewriter(
  targetText: string,
  isActive: boolean,
  charsPerFrame: number = 3
): { displayedText: string; isRevealing: boolean } {
  const [displayedLength, setDisplayedLength] = useState(0);
  const animationRef = useRef<number | null>(null);
  const lastTargetRef = useRef(targetText);

  useEffect(() => {
    // If not active, show full text immediately
    if (!isActive) {
      setDisplayedLength(targetText.length);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    // If target text changed (new content arrived), keep revealing
    if (targetText !== lastTargetRef.current) {
      lastTargetRef.current = targetText;
    }

    // Animation function
    const animate = () => {
      setDisplayedLength((current) => {
        if (current >= targetText.length) {
          animationRef.current = null;
          return current;
        }
        // Reveal more characters
        const next = Math.min(current + charsPerFrame, targetText.length);
        return next;
      });

      // Continue animation if not caught up
      animationRef.current = requestAnimationFrame(animate);
    };

    // Start animation if we're behind
    if (displayedLength < targetText.length && !animationRef.current) {
      animationRef.current = requestAnimationFrame(animate);
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [targetText, isActive, charsPerFrame, displayedLength]);

  const displayedText = targetText.slice(0, displayedLength);
  const isRevealing = isActive && displayedLength < targetText.length;

  return { displayedText, isRevealing };
}
