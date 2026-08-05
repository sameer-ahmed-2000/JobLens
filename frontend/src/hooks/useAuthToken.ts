import { useState, useEffect } from 'react';

export const AUTH_TOKEN_KEY = 'joblens_auth_token';

export const useAuthToken = () => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(AUTH_TOKEN_KEY));

  useEffect(() => {
    const handleAuthChange = () => {
      setToken(localStorage.getItem(AUTH_TOKEN_KEY));
    };

    window.addEventListener('auth-token-changed', handleAuthChange);
    window.addEventListener('storage', handleAuthChange);

    return () => {
      window.removeEventListener('auth-token-changed', handleAuthChange);
      window.removeEventListener('storage', handleAuthChange);
    };
  }, []);

  return token;
};

export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
  window.dispatchEvent(new Event('auth-token-changed'));
};
