import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Bell, Zap, Shield, Clock, ExternalLink, Sparkles, ArrowRight } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

const featureCards = [
  {
    icon: Bell,
    title: "TELEGRAM ALERTS",
    description: "Free instant Telegram notifications the second a spot opens.",
    gradient: "from-emerald-500/20 to-cyan-500/10",
    iconColor: "text-emerald-400",
    borderHover: "hover:border-emerald-500/30",
  },
  {
    icon: Clock,
    title: "24/7 MONITORING",
    description: "We check for new spots every 30 seconds, around the clock.",
    gradient: "from-cyan-500/20 to-blue-500/10",
    iconColor: "text-cyan-400",
    borderHover: "hover:border-cyan-500/30",
  },
  {
    icon: Zap,
    title: "CENT@CASA ONLY",
    description: "Focused on home-based tests. No noise from CENT@UNI.",
    gradient: "from-indigo-500/20 to-purple-500/10",
    iconColor: "text-indigo-400",
    borderHover: "hover:border-indigo-500/30",
  },
  {
    icon: Shield,
    title: "GLOBAL SUPPORT",
    description: "International phone numbers supported for all countries.",
    gradient: "from-purple-500/20 to-pink-500/10",
    iconColor: "text-purple-400",
    borderHover: "hover:border-purple-500/30",
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkExistingSession = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`);
        if (response.data?.telegram_chat_id) {
          navigate('/dashboard');
        }
      } catch {
        // No session yet
      } finally {
        setIsChecking(false);
      }
    };

    checkExistingSession();
  }, [navigate]);

  const handleGetStarted = async () => {
    try {
      const response = await axios.post(`${API}/auth/start`);
      const { needs_telegram } = response.data;
      if (needs_telegram) {
        navigate('/setup-telegram');
      } else {
        navigate('/dashboard');
      }
    } catch (error) {
      console.error("Failed to start session:", error);
      navigate('/dashboard');
    }
  };

  if (isChecking) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="relative">
          <div className="w-10 h-10 border-2 border-emerald-400 border-t-transparent rounded-full spinner" />
          <div className="absolute inset-0 w-10 h-10 border-2 border-cyan-400/30 border-b-transparent rounded-full spinner" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Animated gradient orbs */}
      <div className="orb w-[500px] h-[500px] bg-emerald-500/20 top-[-10%] left-[-5%]" />
      <div className="orb orb-slow w-[400px] h-[400px] bg-cyan-500/15 top-[20%] right-[-5%]" style={{ animationDelay: '-5s' }} />
      <div className="orb w-[300px] h-[300px] bg-indigo-500/10 bottom-[10%] left-[30%]" style={{ animationDelay: '-10s' }} />
      
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-grid-pattern pointer-events-none" />
      
      {/* Gradient fade at top */}
      <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/[0.03] via-transparent to-indigo-500/[0.02] pointer-events-none" />
      
      <div className="relative z-10">
        {/* Nav */}
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-3 h-3 bg-emerald-400 rounded-full pulse-indicator" />
                <div className="absolute inset-0 w-3 h-3 bg-emerald-400 rounded-full animate-ping opacity-20" />
              </div>
              <span className="font-display text-xl font-bold tracking-tight gradient-text-warm">CEnT-S ALERT</span>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
          {/* Hero */}
          <div className="text-left max-w-4xl animate-fadeIn">
            <div className="inline-flex items-center gap-2 glass rounded-full px-5 py-2.5 mb-8">
              <div className="w-2 h-2 bg-emerald-400 rounded-full pulse-indicator" />
              <span className="font-display text-sm text-slate-400 uppercase tracking-widest">
                MONITORING ACTIVE
              </span>
              <Sparkles className="w-3.5 h-3.5 text-emerald-400/60 ml-1" />
            </div>

            <h1 className="font-display text-4xl sm:text-5xl lg:text-7xl font-extrabold tracking-tighter mb-6 leading-[0.95]">
              NEVER MISS A{" "}
              <span className="gradient-text">CENT@CASA</span>
              <br />
              SPOT AGAIN
            </h1>

            <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mb-12 leading-relaxed">
              Get instant alerts when a CEnT-S entrance test spot opens. We monitor the CISIA 
              calendar <span className="text-emerald-400 font-medium">24/7</span> and notify you via Telegram the moment a 
              CENT@CASA position becomes available.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <Button
                data-testid="get-started-btn"
                onClick={handleGetStarted}
                className="group bg-gradient-to-r from-emerald-400 to-cyan-400 text-slate-900 hover:from-emerald-300 hover:to-cyan-300 font-bold rounded-xl uppercase tracking-wider px-8 py-6 text-base transition-all duration-300 hover:shadow-[0_0_40px_rgba(52,211,153,0.3)] hover:-translate-y-0.5"
              >
                Get Started — It's Free
                <ArrowRight className="w-4 h-4 ml-1 transition-transform group-hover:translate-x-1" />
              </Button>

              <a
                href="https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex items-center justify-center glass rounded-xl font-medium uppercase tracking-wider px-8 py-6 text-base transition-all duration-300 hover:border-emerald-500/30 hover:bg-emerald-500/5 text-slate-300 hover:text-white"
              >
                View CISIA Calendar
                <ExternalLink className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </a>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mt-24">
            {featureCards.map((card, idx) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.title}
                  className={`group glass-card rounded-xl p-7 animate-slideUp opacity-0 ${card.borderHover}`}
                  style={{ animationDelay: `${200 + idx * 100}ms`, animationFillMode: 'forwards' }}
                >
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center mb-5 transition-transform duration-300 group-hover:scale-110`}>
                    <Icon className={`w-6 h-6 ${card.iconColor}`} />
                  </div>
                  <h3 className="font-display text-base font-semibold mb-2 text-white">{card.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">
                    {card.description}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Status Section */}
          <div className="mt-24 animate-slideUp opacity-0" style={{ animationDelay: '600ms', animationFillMode: 'forwards' }}>
            <div className="gradient-border rounded-xl p-8">
              <div className="flex items-center gap-4 mb-6">
                <div className="relative">
                  <div className="w-4 h-4 bg-emerald-400 rounded-full pulse-indicator" />
                  <div className="absolute inset-0 w-4 h-4 bg-emerald-400 rounded-full animate-ping opacity-20" />
                </div>
                <span className="font-display text-sm uppercase tracking-widest text-slate-400">
                  SYSTEM STATUS
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">Monitoring</p>
                  <p className="font-display text-2xl font-bold gradient-text-warm">ACTIVE</p>
                </div>
                <div>
                  <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">Check Interval</p>
                  <p className="font-display text-2xl font-bold text-white">30 SEC</p>
                </div>
                <div>
                  <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">Target</p>
                  <p className="font-display text-2xl font-bold text-white">CENT@CASA</p>
                </div>
              </div>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 border-t border-slate-800/50">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full" />
              <span className="font-display text-sm text-slate-500">CEnT-S ALERT</span>
            </div>
            <p className="text-slate-500 text-sm">
              Monitoring{" "}
              <a 
                href="https://testcisia.it" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-emerald-400 hover:text-emerald-300 transition-colors hover:underline"
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
