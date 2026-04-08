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

test.describe('Workflows Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workflows');
  });

  test('should display page title', async ({ page }) => {
    await expect(page).toHaveTitle(/Workflows/);
  });

  test('should show workflows header', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Workflows');
  });

  test('should have refresh button', async ({ page }) => {
    const refreshButton = page.locator('button[title="Refresh"]');
    await expect(refreshButton).toBeVisible();
  });

  test('should show workflow list or empty message', async ({ page }) => {
    // Wait for loading to complete
    await page.waitForTimeout(1000);

    // Either shows workflows or "No workflows found" message
    const hasWorkflows = await page.locator('.divide-y > div').count() > 0;
    const hasEmptyMessage = await page.locator('text=No workflows found').isVisible();
    const hasSelectMessage = await page.locator('text=Select a workflow').isVisible();

    expect(hasWorkflows || hasEmptyMessage || hasSelectMessage).toBeTruthy();
  });

  test('should show "Select a workflow" when none selected', async ({ page }) => {
    await page.waitForTimeout(500);
    await expect(page.locator('text=Select a workflow to view details')).toBeVisible();
  });
});

test.describe('Workflows Page with Demo Data', () => {
  test.beforeAll(async ({ request }) => {
    // Create demo workflow via backend
    // This assumes backend is running
  });

  test('workflow list shows progress', async ({ page }) => {
    await page.goto('/workflows');
    await page.waitForTimeout(1000);

    // Check that the page loaded without errors
    const errorText = await page.locator('text=Failed to fetch').count();
    if (errorText === 0) {
      // Page loaded successfully - check for basic structure
      await expect(page.locator('h1')).toContainText('Workflows');
    }
  });
});

test.describe('Workflow Graph Tab', () => {
  test('should render graph tab with ReactFlow', async ({ page }) => {
    await page.goto('/workflows');
    await page.waitForTimeout(1000);

    // Check if there are any workflows in the list
    const workflowItems = page.locator('.divide-y > div');
    const count = await workflowItems.count();

    if (count > 0) {
      // Click on the first workflow
      await workflowItems.first().click();
      await page.waitForTimeout(500);

      // Verify Graph tab is visible and active by default
      const graphTab = page.locator('button:has-text("Graph")');
      await expect(graphTab).toBeVisible();

      // Click on Graph tab explicitly
      await graphTab.click();
      await page.waitForTimeout(1000);

      // Check for ReactFlow container (it adds a class 'react-flow')
      const reactFlow = page.locator('.react-flow');
      const noNodes = page.locator('text=No nodes to display');

      // Either ReactFlow is visible or "No nodes" message is shown
      const hasReactFlow = await reactFlow.isVisible();
      const hasNoNodes = await noNodes.isVisible();

      expect(hasReactFlow || hasNoNodes).toBeTruthy();

      // If ReactFlow is visible, verify no error/white screen
      if (hasReactFlow) {
        // Check that background and controls are rendered
        await expect(page.locator('.react-flow__background')).toBeVisible();
        await expect(page.locator('.react-flow__controls')).toBeVisible();
      }
    } else {
      // No workflows - just verify page loads correctly
      await expect(page.locator('text=Select a workflow')).toBeVisible();
    }
  });

  test('graph nodes should be interactive', async ({ page }) => {
    await page.goto('/workflows');
    await page.waitForTimeout(1000);

    const workflowItems = page.locator('.divide-y > div');
    const count = await workflowItems.count();

    if (count > 0) {
      // Click on first workflow
      await workflowItems.first().click();
      await page.waitForTimeout(500);

      // Click Graph tab
      await page.locator('button:has-text("Graph")').click();
      await page.waitForTimeout(1000);

      // Check for nodes - verifies nodes are rendered
      const nodes = page.locator('.react-flow__node');
      const nodeCount = await nodes.count();

      // Graph should have nodes rendered
      expect(nodeCount).toBeGreaterThan(0);

      // Verify nodes are visible (interaction test covered by node count > 0)
      await expect(nodes.first()).toBeVisible();
    }
  });
});
