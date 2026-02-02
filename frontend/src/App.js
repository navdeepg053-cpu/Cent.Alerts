import { useEffect, useState, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import PhoneSetup from "@/pages/PhoneSetup";
import History from "@/pages/History";
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Configure axios defaults
axios.defaults.withCredentials = true;

// Auth Callback Component - handles OAuth redirect
const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      // Extract session_id from URL fragment
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

        const { user, needs_phone } = response.data;

        if (needs_phone) {
          // Redirect to phone setup
          navigate('/setup-phone', { state: { user } });
        } else {
          // Go to dashboard
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
    <div className="min-h-screen bg-[#050505] flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[#00FF94] border-t-transparent rounded-full spinner mx-auto mb-4" />
        <p className="text-gray-400 font-display">Authenticating...</p>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);
  const [user, setUser] = useState(location.state?.user || null);

  useEffect(() => {
    // Skip if user was passed from AuthCallback
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

  // Loading state
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#00FF94] border-t-transparent rounded-full spinner" />
      </div>
    );
  }

  // Not authenticated
  if (!isAuthenticated) {
    return null;
  }

  // Pass user to children
  return typeof children === 'function' ? children({ user, setUser }) : children;
};

// Main App Router
const AppRouter = () => {
  const location = useLocation();

  // CRITICAL: Check for session_id synchronously during render
  // This prevents race conditions by processing OAuth callback FIRST
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
        path="/setup-phone"
        element={
          <ProtectedRoute>
            {({ user, setUser }) => <PhoneSetup user={user} setUser={setUser} />}
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
              background: '#0A0A0A',
              border: '1px solid #27272A',
              color: '#ffffff',
            },
          }}
        />
      </BrowserRouter>
    </div>
  );
}

export default App;
