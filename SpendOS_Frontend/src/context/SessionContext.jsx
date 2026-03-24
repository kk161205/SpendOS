/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { getSessions, saveSessions } from '../utils/localStorage';
import { procurementService } from '../services/procurementService';
import { useAuth } from './AuthContext';

const SessionContext = createContext(null);

export const SessionProvider = ({ children }) => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);

  // Use email as the stable unique key (backend returns email, not user_id)
  const userKey = user?.email || 'guest';

  useEffect(() => {
    const initSessions = async () => {
      if (!user) {
        setSessions([]);
        return;
      }
      
      try {
        const history = await procurementService.getHistory();
        setSessions(history);
        saveSessions(userKey, history); 
      } catch {
        setSessions(getSessions(userKey));
      }
    };
    initSessions();
  }, [user, userKey]);

  const addSession = (sessionData) => {
    const newSession = {
      id: sessionData.session_id || sessionData.request_id || crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      product_name: sessionData.product_name,
      category: sessionData.product_category || 'General',
      status: 'completed',
      results: sessionData,
    };
    
    setSessions(prev => {
      const updated = [newSession, ...prev];
      if (user) saveSessions(userKey, updated);
      return updated;
    });
    
    return newSession.id;
  };

  const deleteSession = async (id) => {
    try {
      if (user) {
        await procurementService.deleteSession(id);
      }
      setSessions(prev => {
        const updated = prev.filter(s => s.id !== id);
        if (user) saveSessions(userKey, updated);
        return updated;
      });
    } catch (error) {
      console.error("Failed to delete session:", error);
      throw error;
    }
  };

  const clearCurrentSession = () => setCurrentSession(null);

  return (
    <SessionContext.Provider value={{ 
      sessions, 
      currentSession, 
      setCurrentSession, 
      addSession, 
      deleteSession,
      clearCurrentSession 
    }}>
      {children}
    </SessionContext.Provider>
  );
};

export const useSession = () => useContext(SessionContext);
