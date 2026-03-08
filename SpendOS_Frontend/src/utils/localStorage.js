export const getSessions = (userId) => {
  if (!userId) return [];
  const sessions = localStorage.getItem(`sessions_${userId}`);
  return sessions ? JSON.parse(sessions) : [];
};

export const saveSessions = (userId, sessions) => {
  if (!userId) return;
  localStorage.setItem(`sessions_${userId}`, JSON.stringify(sessions));
};
