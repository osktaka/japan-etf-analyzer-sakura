/** Hook for fetching ETF details */
import { useState, useEffect, useCallback } from 'react';
import { getETFDetail, ETFDetail } from '../api';

interface UseETFDetailState {
  data: ETFDetail | null;
  isLoading: boolean;
  error: Error | null;
}

export function useETFDetail(code: string | null) {
  const [state, setState] = useState<UseETFDetailState>({
    data: null,
    isLoading: false,
    error: null,
  });

  const fetchData = useCallback(async () => {
    if (!code) {
      setState({ data: null, isLoading: false, error: null });
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const data = await getETFDetail(code);
      if (data) {
        setState({ data, isLoading: false, error: null });
      } else {
        setState({
          data: null,
          isLoading: false,
          error: new Error('ETF not found'),
        });
      }
    } catch (err) {
      setState({
        data: null,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Unknown error'),
      });
    }
  }, [code]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refetch: fetchData };
}
