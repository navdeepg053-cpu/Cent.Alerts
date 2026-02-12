import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Bell, Zap, Shield, Clock, ExternalLink, Copy, Check } from "lucide-react";
import { toast } from "sonner";

// Use the backend URL from environment, or empty string for same-origin deployment
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

// Detect in-app browsers (Telegram, Instagram, Facebook, etc.)
const isInAppBrowser = () => {
  const ua = navigator.userAgent || navigator.vendor || window.opera;
  
  // Check for common in-app browser indicators
  const inAppIndicators = [
    'FBAN',      // Facebook
    'FBAV',      // Facebook
    'Instagram', // Instagram
    'Twitter',   // Twitter
    'TelegramBot', // Telegram
    'Telegram',  // Telegram
    'WebView',   // Generic WebView
    'wv',        // Android WebView
  ];
  
  // Check if any indicator is present
  for (const indicator of inAppIndicators) {
    if (ua.includes(indicator)) {
      return true;
    }
  }
  
  // Additional check for Telegram on iOS/Android
  if (ua.includes('Mobile') && (ua.includes('Safari') === false || ua.includes('CriOS') === false)) {
    // Could be Telegram's browser which doesn't identify itself clearly
    // Check for missing standard browser features
    if (window.navigator.standalone !== undefined) {
      return false; // iOS Safari
    }
  }
  
  return false;
};

export default function Landing() {
  const navigate = useNavigate();
  const [isChecking, setIsChecking] = useState(true);
  const [showInAppWarning, setShowInAppWarning] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Check if in-app browser
    if (isInAppBrowser()) {
      setShowInAppWarning(true);
    }
    
    // Check if already authenticated
    const checkExistingAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`);
        if (response.data) {
          navigate('/dashboard');
        }
      } catch {
        // Not authenticated, stay on landing
      } finally {
        setIsChecking(false);
      }
    };

    checkExistingAuth();
  }, [navigate]);

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    toast.success("Link copied! Paste in your browser.");
    setTimeout(() => setCopied(false), 3000);
  };

  const handleOpenInBrowser = () => {
    // Try to open in external browser
    const url = window.location.href;
    
    // For Android
    if (navigator.userAgent.includes('Android')) {
      window.open(`intent://${url.replace(/^https?:\/\//, '')}#Intent;scheme=https;package=com.android.chrome;end`, '_blank');
    } else {
      // For iOS and others, just copy the link
      handleCopyLink();
    }
  };

  if (isChecking) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#00FF94] border-t-transparent rounded-full spinner" />
      </div>
    );
  }

  // Show warning if in Telegram or other in-app browser
  if (showInAppWarning) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-[#0A0A0A] border border-[#27272A] p-8 text-center">
          <div className="w-16 h-16 bg-yellow-500/10 border border-yellow-500/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <ExternalLink className="w-8 h-8 text-yellow-500" />
          </div>
          
          <h1 className="font-display text-2xl font-bold mb-4">
            OPEN IN BROWSER
          </h1>
          
          <p className="text-gray-400 mb-6">
            Google sign-in doesn't work in Telegram's browser. 
            Please open this page in <b className="text-white">Chrome</b>, <b className="text-white">Safari</b>, or your default browser.
          </p>

          <div className="space-y-3">
            <Button
              onClick={handleCopyLink}
              className="w-full bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold rounded-none uppercase tracking-wider py-6"
              data-testid="copy-link-btn"
            >
              {copied ? (
                <>
                  <Check className="w-5 h-5 mr-2" />
                  LINK COPIED!
                </>
              ) : (
                <>
                  <Copy className="w-5 h-5 mr-2" />
                  COPY LINK
                </>
              )}
            </Button>
            
            <p className="text-gray-500 text-sm">
              Then paste in Chrome/Safari to sign up
            </p>

            <button
              onClick={() => setShowInAppWarning(false)}
              className="text-gray-500 text-sm hover:text-white mt-4"
            >
              Continue anyway (may not work)
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] relative overflow-hidden">
      {/* Background effect */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#00FF94]/5 to-transparent pointer-events-none" />
      
      {/* Hero Section */}
      <div className="relative z-10">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-[#00FF94] pulse-indicator" />
              <span className="font-display text-xl font-bold tracking-tight">CEnT-S ALERT</span>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          {/* Hero */}
          <div className="text-left max-w-4xl animate-fadeIn">
            <div className="inline-flex items-center gap-2 bg-[#0A0A0A] border border-[#27272A] px-4 py-2 mb-8">
              <div className="w-2 h-2 bg-[#00FF94] rounded-full pulse-indicator" />
              <span className="font-display text-sm text-gray-400 uppercase tracking-widest">
                MONITORING ACTIVE
              </span>
            </div>

            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tighter mb-6">
              NEVER MISS A{" "}
              <span className="text-[#00FF94] neon-text">CENT@CASA</span>
              <br />
              SPOT AGAIN
            </h1>

            <p className="text-lg text-gray-400 max-w-2xl mb-12 leading-relaxed">
              Get instant alerts when a CEnT-S entrance test spot opens. We monitor the CISIA 
              calendar 24/7 and notify you via Telegram the moment a 
              CENT@CASA position becomes available.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <Button
                data-testid="google-login-btn"
                onClick={handleGoogleLogin}
                className="bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold rounded-none uppercase tracking-wider px-8 py-6 text-base transition-colors hover:shadow-[0_0_20px_rgba(0,255,148,0.4)]"
              >
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Continue with Google
              </Button>

              <a
                href="https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center bg-transparent border border-[#27272A] text-white hover:border-white hover:bg-white/5 font-medium rounded-none uppercase tracking-wider px-8 py-6 text-base transition-colors"
              >
                View CISIA Calendar
              </a>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-24 animate-slideUp delay-200">
            <div className="bg-[#0A0A0A] border border-[#27272A] p-8 card-hover">
              <Bell className="w-8 h-8 text-[#00FF94] mb-4" />
              <h3 className="font-display text-lg font-semibold mb-2">TELEGRAM ALERTS</h3>
              <p className="text-gray-400 text-sm">
                Free instant Telegram notifications the second a spot opens.
              </p>
            </div>

            <div className="bg-[#0A0A0A] border border-[#27272A] p-8 card-hover">
              <Clock className="w-8 h-8 text-[#00FF94] mb-4" />
              <h3 className="font-display text-lg font-semibold mb-2">24/7 MONITORING</h3>
              <p className="text-gray-400 text-sm">
                We check for new spots every 10 minutes, around the clock.
              </p>
            </div>

            <div className="bg-[#0A0A0A] border border-[#27272A] p-8 card-hover">
              <Zap className="w-8 h-8 text-[#00FF94] mb-4" />
              <h3 className="font-display text-lg font-semibold mb-2">CENT@CASA ONLY</h3>
              <p className="text-gray-400 text-sm">
                Focused on home-based tests. No noise from CENT@UNI.
              </p>
            </div>

            <div className="bg-[#0A0A0A] border border-[#27272A] p-8 card-hover">
              <Shield className="w-8 h-8 text-[#00FF94] mb-4" />
              <h3 className="font-display text-lg font-semibold mb-2">GLOBAL SUPPORT</h3>
              <p className="text-gray-400 text-sm">
                International phone numbers supported for all countries.
              </p>
            </div>
          </div>

          {/* Status Section */}
          <div className="mt-24 animate-slideUp delay-400">
            <div className="bg-[#0A0A0A] border border-[#27272A] p-8">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-4 h-4 bg-[#00FF94] rounded-full pulse-indicator shadow-[0_0_10px_#00FF94]" />
                <span className="font-display text-sm uppercase tracking-widest text-gray-400">
                  SYSTEM STATUS
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <p className="text-gray-500 text-sm uppercase tracking-wider mb-1">Monitoring</p>
                  <p className="font-display text-2xl font-bold text-[#00FF94]">ACTIVE</p>
                </div>
                <div>
                  <p className="text-gray-500 text-sm uppercase tracking-wider mb-1">Check Interval</p>
                  <p className="font-display text-2xl font-bold">10 MIN</p>
                </div>
                <div>
                  <p className="text-gray-500 text-sm uppercase tracking-wider mb-1">Target</p>
                  <p className="font-display text-2xl font-bold">CENT@CASA</p>
                </div>
              </div>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 border-t border-[#27272A]">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-[#00FF94]" />
              <span className="font-display text-sm text-gray-500">CEnT-S ALERT</span>
            </div>
            <p className="text-gray-500 text-sm">
              Monitoring{" "}
              <a 
                href="https://testcisia.it" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-[#00FF94] hover:underline"
              >
                testcisia.it
              </a>
              {" "}for CENT@CASA availability
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
