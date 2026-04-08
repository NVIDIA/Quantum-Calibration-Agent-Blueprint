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

import { useMemo, useReducer } from 'react';

// Extracts property names from initial state of reducer to allow typesafe dispatch objects
export type FieldNames<T> = {
  [K in keyof T]: T[K] extends string ? K : K;
}[keyof T];

// Returns the Action Type for the dispatch object to be used for typing in things like context
export type ActionType<T> =
  | { type: 'reset' }
  | { type?: 'change'; field: FieldNames<T>; value: any };

// Returns a typed dispatch and state
export const useCreateReducer = <T>({ initialState }: { initialState: T }) => {
  type Action =
    | { type: 'reset' }
    | { type?: 'change'; field: FieldNames<T>; value: any };

  const reducer = (state: T, action: Action) => {
    if (!action.type) return { ...state, [action.field]: action.value };

    if (action.type === 'reset') return initialState;

    throw new Error();
  };

  const [state, dispatch] = useReducer(reducer, initialState);

  return useMemo(() => ({ state, dispatch }), [state, dispatch]);
};
