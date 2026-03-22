import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for generic error handling and 401s
api.interceptors.response.use(
  (response) => {
    // Standardize success response payload if needed
    return response;
  },
  async (error) => {
    // Network Error or Server Unreachable
    if (!error.response) {
      console.error("API Network Error:", error.message);
      return Promise.reject(
        new Error(
          "Unable to connect to the server. Please check your internet connection.",
        ),
      );
    }

    const { status, data } = error.response;

    const originalRequest = error.config;

    // Handle 401 Unauthorized globally with seamless refresh flow
    if (status === 401 && !originalRequest._retry) {
      // Avoid refresh loop if the refresh endpoint itself returns 401
      if (originalRequest.url.includes('/auth/refresh')) {
        window.location.href = "/login";
        return Promise.reject(error);
      }

      originalRequest._retry = true;
      try {
        // Attempt to refresh the tokens using the HttpOnly refresh cookie
        await axios.post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true });
        
        // If successful, retry the original API call
        return api(originalRequest);
      } catch (refreshError) {
        console.warn("Refresh token expired or invalid. Redirecting to login.");
        if (
          !window.location.pathname.startsWith("/login") &&
          !window.location.pathname.startsWith("/register")
        ) {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    } else if (status === 401) {
      // If we already retried and still got 401, redirect to login
      if (
        !window.location.pathname.startsWith("/login") &&
        !window.location.pathname.startsWith("/register")
      ) {
        window.location.href = "/login";
      }
    }

    // Standardize error message extraction
    let errorMessage = "An unexpected error occurred";
    if (data && data.detail) {
      // FastAPI usually throws { detail: ... }
      errorMessage =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail);
    } else if (data && data.message) {
      errorMessage = data.message;
    } else if (error.message) {
      errorMessage = error.message;
    }

    console.error(`API Error [${status}]:`, errorMessage);

    // Create a new error with the standardized message to be caught by UI
    const standardizedError = new Error(errorMessage);
    standardizedError.status = status;
    standardizedError.response = error.response; // Add response for detail access
    standardizedError.originalError = error;

    return Promise.reject(standardizedError);
  },
);

export default api;
