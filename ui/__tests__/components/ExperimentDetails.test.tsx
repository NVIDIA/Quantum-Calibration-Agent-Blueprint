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

/**
 * Tests for the experiment parameter layout.
 *
 * The parameter grid keeps each label visually attached to its value. It also
 * has to survive narrow containers: the compact chat view and mobile widths
 * are both much narrower than a long parameter name or a JSON.stringify-ed
 * object value, and JSON offers almost no natural wrapping opportunities.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExperimentDetails } from '@/components/Experiments/ExperimentDetails';
import { ExperimentResult } from '@/types/qcal';

jest.mock('next/dynamic', () => () => {
  const MockPlot = () => <div data-testid="mock-plot" />;
  MockPlot.displayName = 'MockPlot';
  return MockPlot;
});

const LONG_NAME =
  'extremely_long_calibration_parameter_name_that_will_not_wrap_naturally';
const LONG_UNBROKEN_VALUE =
  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const NESTED_OBJECT = { pulse: { amplitude: 0.815, shape: 'gaussian' } };

const buildExperiment = (
  params: Record<string, unknown>
): ExperimentResult => ({
  id: '20260727_000000_layout',
  type: 'layout',
  timestamp: '2026-07-27T00:00:00Z',
  status: 'success',
  params,
  results: {},
  arrays: {},
  plots: [],
  notes: '',
  file_path: '',
});

/** Render and open the Parameters tab, which is not the default tab. */
const renderWithParams = (params: Record<string, unknown>) => {
  const utils = render(<ExperimentDetails experiment={buildExperiment(params)} />);
  fireEvent.click(screen.getByRole('button', { name: 'Parameters' }));
  return utils;
};

/** The grid element is the parent of the rendered label cell. */
const gridFor = (labelText: string): HTMLElement => {
  const label = screen.getByText(labelText);
  const grid = label.parentElement;
  if (!grid) {
    throw new Error(`no grid parent found for label "${labelText}"`);
  }
  return grid;
};

describe('ExperimentDetails parameter layout', () => {
  it('renders each label next to its own value in reading order', () => {
    renderWithParams({ amplitude: 0.5, frequency: 5.23 });

    const grid = gridFor('amplitude:');
    const cells = Array.from(grid.children).map((c) => c.textContent);

    expect(cells).toEqual(['amplitude:', '0.5', 'frequency:', '5.23']);
  });

  it('lays the grid out at the width of its container', () => {
    renderWithParams({ amplitude: 0.5 });

    const grid = gridFor('amplitude:');

    // A shrink-to-fit inline grid sizes to its content, which defeats a
    // shrinkable column: the track can shrink but the grid never has to.
    expect(grid.className).not.toContain('inline-grid');
    expect(grid.className).toContain('grid');
    expect(grid.className).toContain('w-full');
  });

  it('gives the value column a shrinkable track', () => {
    renderWithParams({ amplitude: 0.5 });

    const grid = gridFor('amplitude:');

    // Both tracks at max-content means neither can shrink below its longest
    // unwrapped content, so long values push the grid past its container.
    expect(grid.className).not.toContain('grid-cols-[max-content_max-content]');
    expect(grid.className).toContain('minmax(0,1fr)');
  });

  it('caps the label track so it cannot starve the value track', () => {
    renderWithParams({ amplitude: 0.5 });

    const grid = gridFor('amplitude:');

    // An uncapped max-content label track is maximized before the fr track is
    // expanded, so a long enough name takes the whole width and leaves the
    // value nothing. The cap keeps a share of the container for the value.
    expect(grid.className).toContain('min(max-content,45%)');
  });

  it.each([
    ['a long parameter name', { [LONG_NAME]: 0.5 }, `${LONG_NAME}:`],
    ['a long unbroken string', { amplitude: LONG_UNBROKEN_VALUE }, 'amplitude:'],
    ['a nested object', { pulse: NESTED_OBJECT }, 'pulse:'],
  ])(
    'allows both cells to shrink and wrap for %s',
    (_description, params, labelText) => {
      renderWithParams(params as Record<string, unknown>);

      const grid = gridFor(labelText as string);
      const [labelCell, valueCell] = Array.from(grid.children);

      // A grid item's automatic minimum size is its content, so without an
      // explicit override neither cell can shrink no matter what the track
      // definition says.
      for (const cell of [labelCell, valueCell]) {
        expect(cell.className).toContain('min-w-0');
        expect(cell.className).toMatch(/break-words|break-all/);
      }
    }
  );

  it('renders object values as JSON', () => {
    renderWithParams({ pulse: NESTED_OBJECT });

    expect(screen.getByText(JSON.stringify(NESTED_OBJECT))).toBeInTheDocument();
  });

  it('keeps a separator on both cells of every row', () => {
    renderWithParams({ amplitude: 0.5, frequency: 5.23 });

    const grid = gridFor('amplitude:');

    // With Fragment rows there is no row element to carry the border, so each
    // cell has to draw its own or the rule breaks mid-row.
    for (const cell of Array.from(grid.children)) {
      expect(cell.className).toContain('border-b');
    }
  });

  it('reports when there are no parameters', () => {
    renderWithParams({});

    expect(screen.getByText('No parameters available')).toBeInTheDocument();
  });
});
