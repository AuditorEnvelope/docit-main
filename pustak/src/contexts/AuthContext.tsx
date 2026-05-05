"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import apiClient from "@/lib/apiClient";

// Types
interface User {
  id: string;
  github_id: number;
  email: string | null;
  name: string | null;
  username: string | null;
  avatar_url: string | null;
  plan: "free" | "pro" | "team" | "enterprise";
  is_active: boolean;
  created_at: string;
  is_onboarding_complete?: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  token: string | null;
  login: (accessToken: string, refreshToken: string, user: User) => void;
  logout: () => void;
  isAuthenticated: boolean;
  markOnboardingComplete: () => void;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Storage keys
const ACCESS_TOKEN_KEY = "pustak_access_token";
const REFRESH_TOKEN_KEY = "pustak_refresh_token";
const USER_KEY = "pustak_user";

// Backend URL
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      try {
        const accessToken =
          localStorage.getItem(ACCESS_TOKEN_KEY) ||
          localStorage.getItem(LEGACY_ACCESS_TOKEN_KEY);
        const storedUser =
          localStorage.getItem(USER_KEY) || localStorage.getItem(LEGACY_USER_KEY);

        console.log("[AuthContext] Initializing auth...", {
          hasToken: !!accessToken,
          hasUser: !!storedUser,
        });

        if (accessToken && storedUser) {
          // Verify token is still valid
          const response = await fetch(`${BACKEND_URL}/auth/me`, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          });

          console.log(
            "[AuthContext] Token verification response:",
            response.status,
          );

          if (response.ok) {
            const userData = await response.json();
          try {
            // Verify token is still valid using centralized API client
            const response = await apiClient.get<User>("/auth/me");
            console.log(
              "[AuthContext] Token verification response:",
              response.status
            );

            const userData = response.data;
            const normalizedUser: User = {
              ...userData,
              is_onboarding_complete: userData?.is_onboarding_complete ?? false,
            };
            localStorage.setItem(USER_KEY, JSON.stringify(normalizedUser));
            // Keep legacy key synced during migration window.
            localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
            setUser(normalizedUser);
            setToken(accessToken);
            console.log('[AuthContext] Auth initialized successfully');
          } catch (err) {
            // Token invalid or request failed, clear storage
            console.warn("[AuthContext] Token invalid, clearing auth", err);
            clearAuth();
          }
        } else {
          console.warn("[AuthContext] No stored credentials found");
        }
      } catch (error) {
        console.error("Auth initialization error:", error);
        clearAuth();
      } finally {
        setLoading(false);
        console.log("[AuthContext] Auth init complete");
      }
    };

    initAuth();
  }, []);

  const login = (accessToken: string, refreshToken: string, userData: User) => {
    // Store tokens and user data
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    // Keep legacy keys synced so old code paths continue to work.
    localStorage.setItem(LEGACY_ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(LEGACY_REFRESH_TOKEN_KEY, refreshToken);
    const normalizedUser: User = {
      ...userData,
      is_onboarding_complete: userData?.is_onboarding_complete ?? false,
    };
    localStorage.setItem(USER_KEY, JSON.stringify(normalizedUser));
    localStorage.setItem(LEGACY_USER_KEY, JSON.stringify(normalizedUser));
    setUser(normalizedUser);
    setToken(accessToken);
  };

  const logout = () => {
    clearAuth();
    setUser(null);
    setToken(null);
    // Redirect to home
    window.location.href = "/";
  };

  const clearAuth = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY);
    localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY);
    localStorage.removeItem(LEGACY_USER_KEY);
  };

  const markOnboardingComplete = () => {
    setUser((prev) => {
      if (!prev) return prev;
      const updatedUser = { ...prev, is_onboarding_complete: true };
      localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
      return updatedUser;
    });
  };

  const value: AuthContextType = {
    user,
    loading,
    token,
    login,
    logout,
    isAuthenticated: !!user,
    markOnboardingComplete,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Helper to get access token
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return (
    localStorage.getItem(ACCESS_TOKEN_KEY) ||
    localStorage.getItem(LEGACY_ACCESS_TOKEN_KEY)
  );
}

// Helper to get refresh token
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return (
    localStorage.getItem(REFRESH_TOKEN_KEY) ||
    localStorage.getItem(LEGACY_REFRESH_TOKEN_KEY)
  );
}
