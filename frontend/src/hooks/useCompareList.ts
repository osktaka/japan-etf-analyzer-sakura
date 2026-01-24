/** Hook for managing compare list with sessionStorage */
import { useState, useCallback, useEffect } from 'react';
import { MAX_COMPARE_ITEMS } from '../utils';

const STORAGE_KEY = 'etf-compare-list';

export function useCompareList() {
  const [codes, setCodes] = useState<string[]>(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(codes));
  }, [codes]);

  const addCode = useCallback((code: string) => {
    setCodes((prev) => {
      if (prev.includes(code)) return prev;
      if (prev.length >= MAX_COMPARE_ITEMS) return prev;
      return [...prev, code];
    });
  }, []);

  const removeCode = useCallback((code: string) => {
    setCodes((prev) => prev.filter((c) => c !== code));
  }, []);

  const toggleCode = useCallback((code: string) => {
    setCodes((prev) => {
      if (prev.includes(code)) {
        return prev.filter((c) => c !== code);
      }
      if (prev.length >= MAX_COMPARE_ITEMS) return prev;
      return [...prev, code];
    });
  }, []);

  const clearAll = useCallback(() => {
    setCodes([]);
  }, []);

  const isInList = useCallback(
    (code: string) => {
      return codes.includes(code);
    },
    [codes]
  );

  const canAdd = codes.length < MAX_COMPARE_ITEMS;

  return {
    codes,
    count: codes.length,
    canAdd,
    addCode,
    removeCode,
    toggleCode,
    clearAll,
    isInList,
  };
}
