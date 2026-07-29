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

import { fenceLeadingFrontmatter } from '@/utils/app/frontmatter';

describe('fenceLeadingFrontmatter', () => {
  describe('rewrites genuine frontmatter', () => {
    it('fences a skill document header', () => {
      const out = fenceLeadingFrontmatter(
        '---\nname: my-skill\ndescription: does a thing\n---\n\n# Heading\n',
      );

      expect(out).toBe(
        '```yaml\nname: my-skill\ndescription: does a thing\n```\n\n# Heading\n',
      );
    });

    it('handles CRLF line endings', () => {
      const out = fenceLeadingFrontmatter('---\r\nname: x\r\n---\r\n\r\n# H');

      expect(out.startsWith('```yaml\nname: x\n```')).toBe(true);
    });

    it('accepts dotted and underscored keys', () => {
      for (const key of ['meta.version', 'my_key', '_private']) {
        const out = fenceLeadingFrontmatter(`---\n${key}: 1\n---\n\n# H`);
        expect(out.startsWith('```yaml')).toBe(true);
      }
    });

    it('rewrites only the leading block', () => {
      const out = fenceLeadingFrontmatter(
        '---\nname: x\n---\n\n# H\n\n---\n\nfooter\n',
      );

      // The thematic break further down is untouched.
      expect(out).toContain('\n---\n\nfooter');
      expect(out.match(/```yaml/g)).toHaveLength(1);
    });
  });

  describe('leaves everything else alone', () => {
    it('returns a document with no frontmatter unchanged', () => {
      const doc = '# Heading\n\nSome text.\n';
      expect(fenceLeadingFrontmatter(doc)).toBe(doc);
    });

    it('returns empty input as an empty string', () => {
      expect(fenceLeadingFrontmatter('')).toBe('');
    });

    it('does not treat an opening horizontal rule as frontmatter', () => {
      // Both frontmatter and a thematic break open with `---`. A rule is
      // followed by prose, so capturing to the next `---` would swallow the
      // document's introduction into a YAML block.
      const doc = '---\n\nIntro prose.\n\n---\n\nMore text.\n';
      expect(fenceLeadingFrontmatter(doc)).toBe(doc);
    });

    it('does not treat a rule followed immediately by prose as frontmatter', () => {
      const doc = '---\nJust prose here.\n\n---\n\nMore.\n';
      expect(fenceLeadingFrontmatter(doc)).toBe(doc);
    });
  });

  describe('survives a fence inside the frontmatter', () => {
    it('chooses a fence longer than any run of backticks in the body', () => {
      const out = fenceLeadingFrontmatter(
        '---\nname: x\nexample: |\n  ```bash\n  echo hi\n  ```\n---\n\n# H',
      );

      // A plain triple backtick would be closed early by the inner fence,
      // spilling the rest of the frontmatter into the document body.
      expect(out.startsWith('````yaml\n')).toBe(true);
      expect(out).toContain('```bash');
      expect(out).toContain('````\n\n# H');
    });
  });
});
