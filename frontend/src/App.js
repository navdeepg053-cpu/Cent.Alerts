import { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import TelegramSetup from "@/pages/TelegramSetup";
import History from "@/pages/History";
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

axios.defaults.withCredentials = true;

const AutoSession = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(location.state?.user || null);
  const [ready, setReady] = useState(!!location.state?.user);

  useEffect(() => {
    if (location.state?.user) {
      setUser(location.state.user);
      setReady(true);
      return;
    }

    const ensureSession = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`);
        setUser(response.data);
        setReady(true);
      } catch {
        try {
          const startRes = await axios.post(`${API}/auth/start`);
          setUser(startRes.data.user);
          setReady(true);
        } catch (error) {
          console.error("Failed to create session:", error);
          navigate('/');
        }
      }
    };

    ensureSession();
  }, [navigate, location.state]);

  if (!ready) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="relative">
          <div className="w-10 h-10 border-2 border-emerald-400 border-t-transparent rounded-full spinner" />
          <div className="absolute inset-0 w-10 h-10 border-2 border-cyan-400/30 border-b-transparent rounded-full spinner" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>
      </div>
    );
  }

  return typeof children === 'function' ? children({ user, setUser }) : children;
};

const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/dashboard"
        element={
          <AutoSession>
            {({ user, setUser }) => <Dashboard user={user} setUser={setUser} />}
          </AutoSession>
        }
      />
      <Route
        path="/setup-telegram"
        element={
          <AutoSession>
            {({ user, setUser }) => <TelegramSetup user={user} setUser={setUser} />}
          </AutoSession>
        }
      />
      <Route
        path="/history"
        element={
          <AutoSession>
            {({ user }) => <History user={user} />}
          </AutoSession>
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
