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
 * E2E test for HITL (Human-in-the-Loop) resume functionality
 *
 * Prerequisites:
 * 1. Backend server running on port 8000
 * 2. UI running on port 3099
 *
 * Run with:
 *   npx playwright test e2e/hitl-resume.spec.ts --headed
 */

test.describe('HITL Resume', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    page.on('console', msg => {
      if (msg.type() === 'error') console.log('PAGE ERROR:', msg.text());
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    await page.waitForSelector('textarea', { state: 'attached', timeout: 10000 });
  });

  test('approval modal appears and resume works', async ({ page }) => {
    // Focus and type into textarea using page methods
    const textarea = page.locator('textarea').first();

    // Focus the textarea using evaluate
    await page.evaluate(() => {
      const el = document.querySelector('textarea');
      if (el) el.focus();
    });

    // Type character by character - this triggers React onChange properly
    await page.keyboard.type('Run resonator spectroscopy with default parameters', { delay: 10 });

    console.log('Message typed');
    await page.waitForTimeout(500);

    // Press Enter
    await page.keyboard.press('Enter');
    console.log('Enter pressed');

    // Wait for the approval button
    try {
      await page.waitForSelector('button:has-text("Approve")', { timeout: 90000 });
      console.log('Approval button appeared');

      // Take screenshot
      await page.screenshot({ path: 'e2e/screenshots/before-approve.png', fullPage: true });

      // Click approve
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const approveBtn = buttons.find(btn => btn.textContent?.includes('Approve'));
        if (approveBtn) (approveBtn as HTMLButtonElement).click();
      });

      console.log('Clicked Approve button');

      // Wait for response
      await page.waitForTimeout(15000);

      // Take screenshot
      await page.screenshot({ path: 'e2e/screenshots/after-approve.png', fullPage: true });

      // Check for intermediate steps
      const detailsCount = await page.evaluate(() => {
        return document.querySelectorAll('details').length;
      });

      console.log(`Found ${detailsCount} details elements (intermediate steps)`);
      expect(detailsCount).toBeGreaterThan(0);

    } catch (e) {
      await page.screenshot({ path: 'e2e/screenshots/hitl-failure.png', fullPage: true });
      const pageText = await page.evaluate(() => document.body?.textContent);
      console.log('Page text:', pageText?.substring(0, 1500));

      // Log the textarea value to see if it was typed
      const textareaValue = await page.evaluate(() => {
        const ta = document.querySelector('textarea');
        return ta?.value;
      });
      console.log('Textarea value:', textareaValue);

      throw e;
    }
  });

  test('step IDs continue after resume', async ({ page }) => {
    const stepIds: string[] = [];

    // Monitor responses
    page.on('response', async response => {
      const url = response.url();
      if (url.includes('/chat/stream') || url.includes('/chat/resume')) {
        try {
          const text = await response.text();
          const matches = text.matchAll(/"id":\s*"(step_\d+)"/g);
          for (const match of matches) {
            stepIds.push(match[1]);
          }
        } catch { /* ignore */ }
      }
    });

    // Type message
    await page.evaluate(() => {
      const el = document.querySelector('textarea');
      if (el) el.focus();
    });

    await page.keyboard.type('Run qubit spectroscopy with default parameters', { delay: 10 });
    await page.keyboard.press('Enter');

    // Wait for approval button
    await page.waitForSelector('button:has-text("Approve")', { timeout: 90000 });

    console.log('Step IDs before approve:', stepIds);
    const stepCountBeforeApprove = stepIds.length;

    // Click approve
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const approveBtn = buttons.find(btn => btn.textContent?.includes('Approve'));
      if (approveBtn) (approveBtn as HTMLButtonElement).click();
    });

    await page.waitForTimeout(15000);

    console.log('All step IDs:', stepIds);

    const uniqueStepIds = [...new Set(stepIds)];
    console.log('Unique step IDs:', uniqueStepIds);

    expect(stepIds.length).toBe(uniqueStepIds.length);
    expect(stepIds.length).toBeGreaterThan(stepCountBeforeApprove);

    await page.screenshot({ path: 'e2e/screenshots/step-ids-test.png', fullPage: true });
  });
});
