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
 * A leading YAML frontmatter block: `---`, at least one `key:` line, `---`.
 *
 * The opening `key:` is what separates frontmatter from a document that
 * merely starts with a horizontal rule. Both begin `---`, but a rule is
 * followed by prose, so without this the intro of such a document would be
 * captured up to the next `---` and rendered as YAML.
 */
const LEADING_FRONTMATTER =
  /^---\r?\n([A-Za-z_][\w.-]*[ \t]*:[\s\S]*?)\r?\n---(?:\r?\n)*/;

/**
 * Rewrite a document's leading YAML frontmatter into a fenced yaml block.
 *
 * Skill docs and some knowledge files open with frontmatter. Markdown has no
 * notion of it, so it would otherwise render as a horizontal rule followed by
 * raw key/value lines. Fencing it lets the same code block component
 * highlight it as YAML.
 *
 * Documents without frontmatter are returned unchanged.
 */
export const fenceLeadingFrontmatter = (content: string): string => {
  if (!content) {
    return '';
  }

  return content.replace(
    LEADING_FRONTMATTER,
    (_match, body: string) => `${fenceFor(body)}yaml\n${body}\n${fenceFor(body)}\n\n`,
  );
};

/**
 * Pick a fence long enough to contain the body.
 *
 * A frontmatter value can itself hold a fenced example. Using a plain triple
 * backtick would let that inner fence close the generated block early, so the
 * rest of the frontmatter would escape as markdown.
 */
const fenceFor = (body: string): string => {
  let longest = 0;
  for (const run of body.match(/`+/g) ?? []) {
    longest = Math.max(longest, run.length);
  }
  return '`'.repeat(Math.max(3, longest + 1));
};
