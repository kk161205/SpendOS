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

  useEffect(() => {
    const initSessions = async () => {
      if (!user) {
        setSessions([]);
        return;
      }
      
      try {
        const history = await procurementService.getHistory();
        setSessions(history);
        saveSessions(user.user_id, history); 
      } catch {
        setSessions(getSessions(user.user_id));
      }
    };
    initSessions();
  }, [user]);

  const addSession = (sessionData) => {
    const newSession = {
      id: sessionData.request_id || crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      product_name: sessionData.product_name,
      category: sessionData.product_category || 'General',
      status: 'completed',
      results: sessionData,
    };
    
    setSessions(prev => {
      const updated = [newSession, ...prev];
      if (user) saveSessions(user.user_id, updated);
      return updated;
    });
    
    return newSession.id;
  };

  const deleteSession = (id) => {
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== id);
      if (user) saveSessions(user.user_id, updated);
      return updated;
    });
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
