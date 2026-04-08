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

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { SESSION_COOKIE_NAME, HTTP_PROXY_PATH } from './constants';

export default function middleware(req: NextRequest) {
  // Skip middleware for static files and auth routes
  if (
    req.nextUrl.pathname.startsWith('/_next/') ||
    req.nextUrl.pathname.startsWith(`${HTTP_PROXY_PATH}/auth/`) ||
    req.nextUrl.pathname.startsWith('/favicon.ico') ||
    req.nextUrl.pathname.startsWith('/public/')
  ) {
    return NextResponse.next();
  }

  const response = NextResponse.next();

  // Check if session cookie exists
  const sessionCookie = req.cookies.get(SESSION_COOKIE_NAME);

  if (!sessionCookie) {
    // Generate a new session ID for visitors without one
    const sessionId = `session_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;

    // Set the session cookie
    response.cookies.set(SESSION_COOKIE_NAME, sessionId, {
      httpOnly: false,
      sameSite: 'lax',
      path: '/',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 30 * 24 * 60 * 60, // 30 days
    });

    // Add session ID to headers for API routes
    if (req.nextUrl.pathname.startsWith(`${HTTP_PROXY_PATH}/`)) {
      response.headers.set('x-session-id', sessionId);
    }
  } else {
    // Add existing session ID to headers for API routes
    if (req.nextUrl.pathname.startsWith(`${HTTP_PROXY_PATH}/`)) {
      response.headers.set('x-session-id', sessionCookie.value);
    }
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     * 
     * Note: API auth routes are filtered dynamically in the middleware
     * function to respect the HTTP_PROXY_PATH environment variable
     */
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
};
