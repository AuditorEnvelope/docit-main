import { useState, useEffect } from 'react';

/**
 * Simple client-side auth hook that reads directly from localStorage
 * This is a fallback when AuthContext fails during SSR/hydration
 */
export function useClientAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Only runs on client
    const storedToken = localStorage.getItem('pustak_access_token');
    console.log('🔑 useClientAuth - token from localStorage:', !!storedToken);
    setToken(storedToken);
    setLoading(false);
  }, []);

  return { token, loading };
}
