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

import { IconCheck, IconClipboard, IconDownload } from '@tabler/icons-react';
import { FC, memo, MouseEvent, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter/dist/esm';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { useTranslation } from 'next-i18next';

import {
  generateRandomString,
  programmingLanguages,
} from '@/utils/app/codeblock';

interface Props {
  language: string;
  value: string;
}

export const CodeBlock: FC<Props> = memo(({ language, value }) => {
  const { t } = useTranslation('markdown');
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const formattedValue = (() => {
    if (language !== 'json') {
      return value;
    }
    try {
      return JSON.stringify(JSON.parse(value.replaceAll("'", '"')), null, 2);
    } catch {
      return value;
    }
  })();

  const copyToClipboard = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      return;
    }

    navigator.clipboard.writeText(formattedValue).then(() => {
      setIsCopied(true);

      setTimeout(() => {
        setIsCopied(false);
      }, 2000);
    });
  };

  const downloadAsFile = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    const fileExtension = programmingLanguages[language] || '.file';
    const suggestedFileName = `file-${generateRandomString(
      3,
      true,
    )}${fileExtension}`;

    if (!suggestedFileName) {
      return;
    }

    const blob = new Blob([formattedValue], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = suggestedFileName;
    link.href = url;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="codeblock relative font-sans text-[16px]">
      <div className="flex items-center justify-between py-1.5 px-4 bg-[#282c34] rounded-t">
        <span className="text-xs lowercase text-white">{language}</span>

        <div className="flex items-center">
          <button
            className="flex gap-1.5 items-center rounded bg-none p-1 text-xs text-white"
            onClick={(e) => copyToClipboard(e)}
          >
            {isCopied ? <IconCheck size={18} /> : <IconClipboard size={18} />}
            {isCopied ? t('Copied!') : t('Copy code')}
          </button>
          <button
            className="flex items-center rounded bg-none p-1 text-xs text-white"
            onClick={(e) => downloadAsFile(e)}
          >
            <IconDownload size={18} />
          </button>
        </div>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          maxWidth: '100%',
          maxHeight: '50vh',
          display: 'block',
          boxSizing: 'border-box',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          overflowX: 'auto',
          overflowY: 'auto',
        }}
        wrapLongLines={true} // Ensures long lines wrap instead of forcing width expansion
      >
        {formattedValue}
      </SyntaxHighlighter>
    </div>
  );
});
CodeBlock.displayName = 'CodeBlock';
