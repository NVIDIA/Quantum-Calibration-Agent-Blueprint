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

import { saveFolders } from '@/utils/app/folders';

// Adjust according to your utility functions' locations
import { v4 as uuidv4 } from 'uuid';

export const useFolderOperations = ({ folders, dispatch }) => {
  const handleCreateFolder = (name, type) => {
    const newFolder = {
      id: uuidv4(), // Ensure you have uuid imported or an alternative way to generate unique ids
      name,
      type,
    };

    const updatedFolders = [...folders, newFolder];
    dispatch({ field: 'folders', value: updatedFolders });
    saveFolders(updatedFolders); // Assuming you have a utility function to persist folders change
  };

  const handleDeleteFolder = (folderId) => {
    const updatedFolders = folders.filter((folder) => folder.id !== folderId);
    dispatch({ field: 'folders', value: updatedFolders });
    saveFolders(updatedFolders); // Persist the updated list after deletion
  };

  const handleUpdateFolder = (folderId, name) => {
    const updatedFolders = folders.map((folder) =>
      folder.id === folderId ? { ...folder, name } : folder,
    );
    dispatch({ field: 'folders', value: updatedFolders });
    saveFolders(updatedFolders); // Persist the updated list
  };

  return { handleCreateFolder, handleDeleteFolder, handleUpdateFolder };
};
