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

import { IconDeviceDesktop, IconFlask, IconBook, IconListCheck } from '@tabler/icons-react';
import { useContext } from 'react';
import { useTranslation } from 'next-i18next';

import HomeContext from '@/pages/api/home/home.context';
import { ViewMode } from '@/pages/api/home/home.state';

export const ModeSelector = () => {
  const { t } = useTranslation('sidebar');

  const {
    state: { viewMode },
    dispatch,
  } = useContext(HomeContext);

  const handleModeChange = (mode: ViewMode) => {
    dispatch({ field: 'viewMode', value: mode });
    sessionStorage.setItem('viewMode', mode);
  };

  return (
    <div className="flex flex-col space-y-1 border-t border-white/20 pt-1 text-sm">
      <button
        className={`flex w-full cursor-pointer select-none items-center gap-3 rounded-md py-3 px-3 text-[14px] leading-3 text-white transition-colors duration-200 ${
          viewMode === 'apparatus'
            ? 'bg-gray-500/20'
            : 'hover:bg-gray-500/10'
        }`}
        onClick={() => handleModeChange('apparatus')}
      >
        <div><IconDeviceDesktop size={18} /></div>
        <span>{t('Apparatus')}</span>
      </button>

      <button
        className={`flex w-full cursor-pointer select-none items-center gap-3 rounded-md py-3 px-3 text-[14px] leading-3 text-white transition-colors duration-200 ${
          viewMode === 'experiments'
            ? 'bg-gray-500/20'
            : 'hover:bg-gray-500/10'
        }`}
        onClick={() => handleModeChange('experiments')}
      >
        <div><IconFlask size={18} /></div>
        <span>{t('Experiments')}</span>
      </button>

      <button
        className={`flex w-full cursor-pointer select-none items-center gap-3 rounded-md py-3 px-3 text-[14px] leading-3 text-white transition-colors duration-200 ${
          viewMode === 'workflows'
            ? 'bg-gray-500/20'
            : 'hover:bg-gray-500/10'
        }`}
        onClick={() => handleModeChange('workflows')}
      >
        <div><IconListCheck size={18} /></div>
        <span>{t('Workflows')}</span>
      </button>

      <button
        className={`flex w-full cursor-pointer select-none items-center gap-3 rounded-md py-3 px-3 text-[14px] leading-3 text-white transition-colors duration-200 ${
          viewMode === 'knowledge'
            ? 'bg-gray-500/20'
            : 'hover:bg-gray-500/10'
        }`}
        onClick={() => handleModeChange('knowledge')}
      >
        <div><IconBook size={18} /></div>
        <span>{t('Knowledge')}</span>
      </button>
    </div>
  );
};
