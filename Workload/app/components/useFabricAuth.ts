/**
 * Workload/app/components/useFabricAuth.ts
 *
 * React hook to obtain access tokens for delegated (OBO) flows.
 *
 * This hook wraps the Fabric Workload Client's token acquisition and
 * exposes functions to obtain user access tokens for use in delegated
 * authorization scenarios (passing user_assertion to connectors).
 *
 * Usage:
 *   const { getUserToken, getAccessToken, isLoading, error } = useFabricAuth(workloadClient);
 *   const userToken = await getUserToken(); // user access token for delegated use
 *   const appToken = await getAccessToken(); // app/workload token if needed
 */

import { useState, useCallback } from 'react';
import { WorkloadClientAPI } from '@ms-fabric/workload-client';

interface UseFabricAuthReturn {
  getUserToken: () => Promise<string>;
  getAccessToken: () => Promise<string>;
  isLoading: boolean;
  error: Error | null;
}

/**
 * useFabricAuth — obtain user or app tokens from Fabric Workload Client.
 *
 * The Fabric Workload Client provides methods to get tokens that the
 * frontend can pass to the backend for OBO (On-Behalf-Of) delegated flows.
 *
 * @param workloadClient The Fabric Workload Client instance
 * @returns Object with methods to get tokens and loading/error state
 */
export const useFabricAuth = (workloadClient: WorkloadClientAPI | undefined): UseFabricAuthReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const getUserToken = useCallback(async (): Promise<string> => {
    if (!workloadClient) {
      throw new Error('Workload client not available');
    }
    setIsLoading(true);
    setError(null);
    try {
      // Request a user access token (interactive auth if required).
      // The workloadClient exposes a method to acquire tokens.
      const token = await workloadClient.getAccessToken?.(['user.read']);
      if (!token) {
        throw new Error('Failed to acquire user token');
      }
      return token;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [workloadClient]);

  const getAccessToken = useCallback(async (): Promise<string> => {
    if (!workloadClient) {
      throw new Error('Workload client not available');
    }
    setIsLoading(true);
    setError(null);
    try {
      // Request app/workload access token.
      const token = await workloadClient.getAccessToken?.();
      if (!token) {
        throw new Error('Failed to acquire access token');
      }
      return token;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [workloadClient]);

  return { getUserToken, getAccessToken, isLoading, error };
};
