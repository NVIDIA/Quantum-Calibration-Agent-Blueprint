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
 * Validates media URLs to prevent SSRF and protocol injection
 * @param url - URL to validate
 * @returns boolean indicating if URL is safe to load
 */
export function isValidMediaURL(url: string): boolean {
  // Block empty or non-string URLs
  if (!url || typeof url !== 'string') return false;

  if (url.startsWith("data:")) {
    // Allow data URLs for images/videos
    if (! /^data:image\/(png|jpeg);base64,/.test(url)) {
      return false;
    }
  } else {
    // Block excessively long URLs to prevent DoS, but allow embedded data URLs
    if (url.length > 2048) {
      return false;
    }
  }

  // Block control characters that can confuse parsers
  for (let i = 0; i < url.length; i++) {
    const charCode = url.charCodeAt(i);
    if (charCode <= 0x1F || charCode === 0x7F) {
      return false;
    }
  }

  // Must be a valid URL
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(url);
  } catch (error) {
    return false;
  }

  // Only allow HTTP/HTTPS protocols for images/videos
  if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:' && parsedUrl.protocol !== 'data:') {
    return false;
  }

  // Block embedded credentials for security
  if (parsedUrl.username || parsedUrl.password) return false;

  // Block internal/private network addresses to prevent SSRF
  const hostname = parsedUrl.hostname.toLowerCase();

  // Block IPv6 private ranges (but allow loopback ::1 for dev)
  if (hostname.includes(':')) {
    if (hostname.startsWith('fe80:') ||
      hostname.startsWith('fc') ||
      hostname.startsWith('fd')) {
      return false;
    }
  }

  // Block IPv4 private, link-local, and reserved ranges (but allow 127.x.x.x for dev)
  if (hostname.match(/^0\./) ||                           // 0.0.0.0/8 - Current network
    hostname.match(/^10\./) ||                          // 10.0.0.0/8 - Private
    hostname.match(/^169\.254\./) ||                    // 169.254.0.0/16 - Link-local
    hostname.match(/^172\.(1[6-9]|2[0-9]|3[0-1])\./) || // 172.16.0.0/12 - Private
    hostname.match(/^192\.168\./) ||                    // 192.168.0.0/16 - Private
    hostname.match(/^22[4-9]\./) ||                     // 224-229.x.x.x - Multicast
    hostname.match(/^2[3-4][0-9]\./) ||                 // 230-249.x.x.x - Multicast/Reserved
    hostname.match(/^25[0-5]\./)) {                     // 250-255.x.x.x - Reserved
    return false;
  }

  return true;
}
