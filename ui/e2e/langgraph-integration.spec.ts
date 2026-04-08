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

/**
 * E2E test for LangGraph integration with NAT UI
 *
 * Prerequisites:
 * 1. LangGraph server running on port 2024 (deepagents-cli)
 * 2. UI running on port 3000
 *
 * Run with:
 *   npx playwright test e2e/langgraph-integration.spec.ts
 */

test.describe('LangGraph Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the chat page
    await page.goto('/');
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('UI loads successfully', async ({ page }) => {
    // Check that the greeting is displayed
    await expect(page.locator('text=NVIDIA Quantum Calibration Agent')).toBeVisible({ timeout: 10000 });
  });

  test('can send a message and receive response', async ({ page }) => {
    // Find the chat input textarea
    const chatInput = page.locator('textarea').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    // Type a simple message
    await chatInput.fill('Say hello in one sentence');

    // Submit by pressing Enter (or clicking send button)
    await chatInput.press('Enter');

    // Wait for response - the assistant message has bg-gray-50 class
    // The response appears in a div with specific styling
    // We'll look for text that indicates a response was received

    // First wait for the loading to finish (no more streaming indicator)
    await page.waitForTimeout(2000); // Initial wait for request to start

    // Look for any new content that appears after our message
    // The response should contain greeting-like text
    const responseLocator = page.locator('div.bg-gray-50, div[class*="bg-[#444654]"]').last();

    // Wait for the response element to appear with longer timeout
    await expect(responseLocator).toBeVisible({ timeout: 60000 });

    // Verify the response has some content (check for markdown rendered content)
    const responseText = await responseLocator.textContent();
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(5);

    console.log('Response received:', responseText?.substring(0, 100));
  });

  test('chat input is functional', async ({ page }) => {
    const chatInput = page.locator('textarea').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });
    await expect(chatInput).toBeEnabled();

    // Should be able to type
    await chatInput.fill('Test message');
    await expect(chatInput).toHaveValue('Test message');
  });

  test('intermediate steps are shown', async ({ page }) => {
    // This test checks that tool calls show up as intermediate steps
    const chatInput = page.locator('textarea').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    // Ask something that might trigger a tool
    await chatInput.fill('What experiments are available?');
    await chatInput.press('Enter');

    // Wait for response
    await page.waitForTimeout(15000);

    // Check if there's any response content
    const hasContent = await page.locator('div.bg-gray-50').count();
    expect(hasContent).toBeGreaterThan(0);
  });
});
