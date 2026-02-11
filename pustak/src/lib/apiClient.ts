import axios, { type AxiosRequestConfig, type AxiosResponse } from "axios";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000/api/v1";

// Ensure we always talk to the API root (including /api/v1 when omitted)
const apiBase = (() => {
  const normalized = BACKEND_URL.replace(/\/$/, "");
  const hasApiSuffix = /\/api(\/v\d+)?$/i.test(normalized);
  return hasApiSuffix ? normalized : `${normalized}/api/v1`;
})();

const ACCESS_TOKEN_KEY = "pustak_access_token";
const REFRESH_TOKEN_KEY = "pustak_refresh_token";
const USER_KEY = "pustak_user";

export const apiClient = axios.create({
  baseURL: apiBase,
  withCredentials: true,
});

// Attach Authorization header from localStorage on the client
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) {
      config.headers = config.headers ?? {};
      if (!("Authorization" in config.headers)) {
        (config.headers as any).Authorization = `Bearer ${token}`;
      }
    }
  }

  return config;
});

// Global 401 handling: clear auth and redirect to login
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: any) => {
    const status = error?.response?.status;

    if (status === 401 && typeof window !== "undefined") {
      try {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      } catch {
        // Swallow storage errors; we'll still redirect
      }

      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
