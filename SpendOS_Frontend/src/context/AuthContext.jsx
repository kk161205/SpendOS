/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authService } from "../services/authService";

const AuthContext = createContext(null);

const getInitialUser = () => {
  if (typeof window === "undefined") return null;
  const storedUser = localStorage.getItem("user");
  if (storedUser) {
    try {
      return JSON.parse(storedUser);
    } catch {
      localStorage.removeItem("user");
      return null;
    }
  }
  return null;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(getInitialUser());
  const [isAuthenticated, setIsAuthenticated] = useState(!!user);
  const [isLoading] = useState(false);

  // We keep a mount effect for any side effects needed, but none right now
  useEffect(() => {
    // No-op
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem("user");
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      const data = await authService.login(email, password);
      setUser(data.user);
      localStorage.setItem("user", JSON.stringify(data.user));
      setIsAuthenticated(true);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error:
          error.response?.data?.detail ||
          "Login failed. Please check your credentials.",
      };
    }
  }, []);

  const register = useCallback(async (email, password, fullName) => {
    try {
      await authService.register(email, password, fullName);
      return await login(email, password);
    } catch (error) {
      let msg = error.message || "Registration failed.";
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === "string") {
          msg = detail;
        } else if (Array.isArray(detail)) {
          msg = detail[0]?.msg || msg;
        } else if (typeof detail === "object") {
          msg = detail.message || JSON.stringify(detail);
        }
      }
      return { success: false, error: msg };
    }
  }, [login]);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
