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
import * as path from 'path';

const SCREENSHOT_DIR = path.join(__dirname, '../../docs/_static/images/usage');

// Use port 3000 (proxy gateway) for proper backend connection
// Viewport 1.5x default (1280x720 -> 1920x1080)
test.use({
  baseURL: 'http://localhost:3000',
  viewport: { width: 1920, height: 1080 }
});

test.describe('Documentation Screenshots', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Wait for UI to fully render
    await page.waitForTimeout(1000);
  });

  test('capture web-ui-overview', async ({ page }) => {
    // Capture the full UI with chat view (default)
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'web-ui-overview.png'),
      fullPage: false,
    });
  });

  test('capture chat-interface', async ({ page }) => {
    // Focus on the chat area
    const chatArea = page.locator('[class*="Chat"]').first();
    if (await chatArea.isVisible()) {
      await chatArea.screenshot({
        path: path.join(SCREENSHOT_DIR, 'chat-interface.png'),
      });
    } else {
      // Fallback to full page
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'chat-interface.png'),
        fullPage: false,
      });
    }
  });

  test('capture apparatus-panel', async ({ page }) => {
    // Navigate to Apparatus view
    await page.click('button:has-text("Apparatus")');
    await expect(page.locator('h1:has-text("Apparatus")')).toBeVisible();
    await page.waitForTimeout(500);

    // Click on rabi_oscillation experiment
    await page.click('text=rabi_oscillation');
    await page.waitForTimeout(500);

    // Try to expand code panel if available
    const codeToggle = page.locator('button:has-text("Code"), button:has-text("Source"), [aria-label*="code"]').first();
    if (await codeToggle.isVisible()) {
      await codeToggle.click();
      await page.waitForTimeout(300);
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'apparatus-panel.png'),
      fullPage: false,
    });
  });

  test('capture experiments-dashboard', async ({ page }) => {
    // Navigate to Experiments view
    await page.click('button:has-text("Experiments")');
    await expect(page.locator('h1:has-text("Experiments Dashboard")')).toBeVisible();
    await page.waitForTimeout(500);

    // Click on the first experiment row (px-4 py-3 div with border-l-4)
    const experimentRow = page.locator('.border-l-4.cursor-pointer').first();
    if (await experimentRow.isVisible()) {
      await experimentRow.click();
      // Wait for plots to load in the bottom panel
      await page.waitForTimeout(3000);
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'experiment-details.png'),
      fullPage: false,
    });
  });

  test('capture knowledge-panel', async ({ page }) => {
    // Navigate to Knowledge view
    await page.click('button:has-text("Knowledge")');
    await expect(page.locator('h1:has-text("Knowledge Base")')).toBeVisible();
    await page.waitForTimeout(500);

    // Click on analysis script to show content
    const analysisScript = page.locator('text=analysis script', { exact: false }).first();
    if (await analysisScript.isVisible()) {
      await analysisScript.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'knowledge-panel.png'),
      fullPage: false,
    });
  });

  test('capture workflow-dag', async ({ page }) => {
    // Navigate to Workflows view
    await page.click('button:has-text("Workflows")');
    await expect(page.locator('h1:has-text("Workflows")')).toBeVisible();
    await page.waitForTimeout(500);

    // Click on the running workflow to show the DAG
    const runningWorkflow = page.locator('text=running').first();
    if (await runningWorkflow.isVisible()) {
      await runningWorkflow.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'workflow-dag.png'),
      fullPage: false,
    });
  });
});
