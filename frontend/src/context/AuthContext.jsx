import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('insuraflow_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [capabilities, setCapabilities] = useState({
    live_gemini_configured: false,
    gemini_model: 'gemini-2.5-flash',
    demo_mode_enabled: true,
  });
  const [preferDemoMode, setPreferDemoMode] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('insuraflow_token');
    if (!token) {
      setLoading(false);
      return;
    }
    authService
      .getMe()
      .then((res) => {
        setUser(res.data.user);
        const caps = res.data.system_capabilities || {};
        setCapabilities(caps);
        setPreferDemoMode(!caps.live_gemini_configured);
      })
      .catch(() => {
        localStorage.removeItem('insuraflow_token');
        localStorage.removeItem('insuraflow_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await authService.login(email, password);
    const { access_token, user: userData } = res.data;
    localStorage.setItem('insuraflow_token', access_token);
    localStorage.setItem('insuraflow_user', JSON.stringify(userData));
    setUser(userData);
    const meRes = await authService.getMe();
    const caps = meRes.data.system_capabilities || {};
    setCapabilities(caps);
    setPreferDemoMode(!caps.live_gemini_configured);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('insuraflow_token');
    localStorage.removeItem('insuraflow_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        capabilities,
        preferDemoMode,
        setPreferDemoMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
