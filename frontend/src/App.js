import { useEffect, useState, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import TelegramSetup from "@/pages/TelegramSetup";
import History from "@/pages/History";
import { Toaster } from "@/components/ui/sonner";

// Use the backend URL from environment, or empty string for same-origin deployment
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = location.hash;
      const params = new URLSearchParams(hash.replace('#', ''));
      const sessionId = params.get('session_id');

      if (!sessionId) {
        navigate('/');
        return;
      }

      try {
        const response = await axios.post(`${API}/auth/session`, {
          session_id: sessionId
        });

        const { user, needs_telegram } = response.data;

        if (needs_telegram) {
          navigate('/setup-telegram', { state: { user } });
        } else {
          navigate('/dashboard', { state: { user } });
        }
      } catch (error) {
        console.error('Auth error:', error);
        navigate('/');
      }
    };

    processAuth();
  }, [navigate, location]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <div className="relative mx-auto mb-4 w-10 h-10">
          <div className="w-10 h-10 border-2 border-emerald-400 border-t-transparent rounded-full spinner" />
          <div className="absolute inset-0 w-10 h-10 border-2 border-cyan-400/30 border-b-transparent rounded-full spinner" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>
        <p className="text-slate-400 font-display">Authenticating...</p>
      </div>
    </div>
  );
};

const ProtectedRoute = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);
  const [user, setUser] = useState(location.state?.user || null);

  useEffect(() => {
    if (location.state?.user) {
      setUser(location.state.user);
      setIsAuthenticated(true);
      return;
    }

    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`);
        setUser(response.data);
        setIsAuthenticated(true);
      } catch (error) {
        setIsAuthenticated(false);
        navigate('/');
      }
    };

    checkAuth();
  }, [navigate, location.state]);

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="relative">
          <div className="w-10 h-10 border-2 border-emerald-400 border-t-transparent rounded-full spinner" />
          <div className="absolute inset-0 w-10 h-10 border-2 border-cyan-400/30 border-b-transparent rounded-full spinner" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return typeof children === 'function' ? children({ user, setUser }) : children;
};

const AppRouter = () => {
  const location = useLocation();

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            {({ user, setUser }) => <Dashboard user={user} setUser={setUser} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/setup-telegram"
        element={
          <ProtectedRoute>
            {({ user, setUser }) => <TelegramSetup user={user} setUser={setUser} />}
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            {({ user }) => <History user={user} />}
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

function App() {
  return (
    <div className="dark">
      <BrowserRouter>
        <AppRouter />
        <Toaster 
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'rgba(15, 23, 42, 0.8)',
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              color: '#f1f5f9',
              borderRadius: '12px',
            },
          }}
        />
      </BrowserRouter>
    </div>
  );
}

export default App;
