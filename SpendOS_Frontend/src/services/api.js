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
  (error) => {
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

    // Handle 401 Unauthorized globally
    if (status === 401) {
      console.warn("Authentication expired or invalid. Redirecting to login.");
      // Only redirect if not already on login/register to avoid loops
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
