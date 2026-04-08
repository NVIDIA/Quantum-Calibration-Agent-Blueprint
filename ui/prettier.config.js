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

module.exports = {
  trailingComma: 'all',
  singleQuote: true,
  plugins: [
    'prettier-plugin-tailwindcss',
    '@trivago/prettier-plugin-sort-imports',
  ],
  importOrder: [
    'react', // React
    '^react-.*$', // React-related imports
    '^next', // Next-related imports
    '^next-.*$', // Next-related imports
    '^next/.*$', // Next-related imports
    '^.*/hooks/.*$', // Hooks
    '^.*/services/.*$', // Services
    '^.*/utils/.*$', // Utils
    '^.*/types/.*$', // Types
    '^.*/pages/.*$', // Components
    '^.*/components/.*$', // Components
    '^[./]', // Other imports
    '.*', // Any uncaught imports
  ],
  importOrderSeparation: true,
  importOrderSortSpecifiers: true,
};
