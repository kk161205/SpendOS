import React, { createContext, useContext, useState, useEffect } from "react";
import { authService } from "../services/authService";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
        setIsAuthenticated(true);
      } catch (err) {
        logout();
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const data = await authService.login(email, password);
      setUser(data.user);
      localStorage.setItem('user', JSON.stringify(data.user));
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
  };

  const register = async (email, password, fullName) => {
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
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (e) {}
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
