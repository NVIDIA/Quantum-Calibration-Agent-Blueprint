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

import { test, expect } from '@playwright/test';

test('debug chat flow', async ({ page }) => {
  // Go to chat
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');

  // Screenshot initial state
  await page.screenshot({ path: '/tmp/debug-1-initial.png' });

  // Find and fill chat input
  const chatInput = page.locator('textarea').first();
  await expect(chatInput).toBeVisible({ timeout: 10000 });
  await chatInput.click();
  await chatInput.fill('Hello');

  await page.screenshot({ path: '/tmp/debug-2-typed.png' });

  // Find send button (look for button near the textarea)
  const sendButton = page.locator('button').last();
  console.log('Send button found:', await sendButton.isVisible());

  // Click send
  await sendButton.click();

  // Wait and take screenshots at intervals
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/debug-3-after2s.png' });

  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/debug-4-after7s.png' });

  await page.waitForTimeout(10000);
  await page.screenshot({ path: '/tmp/debug-5-after17s.png' });

  // Get page content
  const content = await page.content();
  console.log('Page has content length:', content.length);

  // Check for any error messages
  const errorText = await page.locator('text=/error|failed|timeout/i').count();
  console.log('Error elements found:', errorText);
});
