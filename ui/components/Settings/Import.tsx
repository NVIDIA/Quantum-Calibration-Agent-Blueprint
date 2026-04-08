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

import { IconFileImport } from '@tabler/icons-react';
import { FC } from 'react';
import toast from 'react-hot-toast';

import { useTranslation } from 'next-i18next';

import { SupportedExportFormats } from '@/types/export';

import { SidebarButton } from '../Sidebar/SidebarButton';

import { validateImportData } from '@/utils/security/import-validation';

interface Props {
  onImport: (data: SupportedExportFormats) => void;
}

export const Import: FC<Props> = ({ onImport }) => {
  const { t } = useTranslation('sidebar');
  return (
    <>
      <input
        id="import-file"
        className="sr-only"
        tabIndex={-1}
        type="file"
        accept=".json"
        onChange={(e) => {
          if (!e.target.files?.length) return;

          const file = e.target.files[0];
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const rawContent = e.target?.result as string;
              
              // Validate and sanitize the imported data
              const validatedData = validateImportData(rawContent);
              
              if (validatedData) {
                onImport(validatedData);
                toast.success('Import successful!');
              }
              // Error messages are handled by validateImportData
            } catch (error) {
              console.error('Import error:', error);
              toast.error('Failed to import file. Please check the file format.');
            }
          };
          
          reader.onerror = () => {
            toast.error('Failed to read file. Please try again.');
          };
          
          reader.readAsText(file);
        }}
      />

      <SidebarButton
        text={t('Import data')}
        icon={<IconFileImport size={18} />}
        onClick={() => {
          const importFile = document.querySelector(
            '#import-file',
          ) as HTMLInputElement;
          if (importFile) {
            importFile.click();
          }
        }}
      />
    </>
  );
};
