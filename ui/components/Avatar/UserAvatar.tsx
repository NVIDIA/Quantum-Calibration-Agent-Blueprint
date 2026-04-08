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

import React from 'react';

import { getInitials } from '@/utils/app/helper';

export const UserAvatar = ({ src = '', height = 30, width = 30 }) => {
  const profilePicUrl = src || ``;

  const onError = (event: { target: { src: string } }) => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
            <rect width="100%" height="100%" fill="#fff"/>
            <text x="50%" y="50%" alignment-baseline="middle" text-anchor="middle" fill="#333" font-size="16" font-family="Arial, sans-serif">
                user
            </text>
        </svg>`;
    event.target.src = `data:image/svg+xml;base64,${window.btoa(svg)}`;
  };

  return (
    <img
      src={profilePicUrl}
      alt={'user-avatar'}
      width={width}
      height={height}
      title={'user-avatar'}
      className="rounded-full max-w-full h-auto border border-[#76b900]"
      onError={onError}
    />
  );
};
