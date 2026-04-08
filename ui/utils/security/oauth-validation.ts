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
 * OAuth URL validation to prevent open redirect attacks
 * @param raw - URL to validate
 * @returns boolean indicating if URL is safe for OAuth redirects
 */
export function isValidConsentPromptURL(raw: string): boolean {
  // 1) quick reject: control chars or whitespace that can confuse parsers/logs
  //    (CR, LF, TAB, VT, FF, and space)
  if (/[ \t\r\n\v\f]/.test(raw)) return false;

  // 2) must be absolute & parseable
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return false;
  }

  // 3) protocol: only http(s)
  if (u.protocol !== "http:" && u.protocol !== "https:") return false;

  // 4) forbid embedded credentials (userinfo)
  if (u.username || u.password) return false;

  // 5) optional: cap length to reduce abuse surface
  if (raw.length > 8192) return false;

  return true;
}

