import { useEffect, useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { 
  RefreshCw, 
  Bell, 
  ExternalLink,
  Clock,
  History,
  Send,
  ArrowUpRight,
  Activity,
  Home
} from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

function AvailableSpotCard({ spot }) {
  return (
    <div className="glass-card rounded-xl p-4 border-emerald-500/20 hover:border-emerald-500/30">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-display font-semibold text-white">
            {spot.university}
          </p>
          <p className="text-slate-400 text-sm">
            {spot.city}, {spot.region}
          </p>
        </div>
        <div className="text-right">
          <p className="font-display font-bold gradient-text-warm">
            {spot.spots} spots
          </p>
          <p className="text-slate-500 text-xs">
            Deadline: {spot.registration_deadline}
          </p>
        </div>
      </div>
    </div>
  );
}

function SpotTableRow({ spot }) {
  const isAvailable = spot.status && spot.status.toUpperCase().includes("DISPONIBILI");
  
  return (
    <tr className="border-b border-slate-800/30 hover:bg-emerald-500/[0.02] transition-colors">
      <td className="p-4">
        <span
          className={`inline-flex items-center gap-2 px-3 py-1 text-xs font-display uppercase tracking-wider ${
            isAvailable ? "status-available" : "status-full"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isAvailable ? "bg-emerald-400" : "bg-red-400"
            }`}
          />
          {isAvailable ? "AVAILABLE" : "FULL"}
        </span>
      </td>
      <td className="p-4 font-display text-sm">{spot.university}</td>
      <td className="p-4 text-slate-400 text-sm">
        {spot.city}, {spot.region}
      </td>
      <td className="p-4 font-display text-sm">{spot.test_date}</td>
      <td className="p-4 text-slate-400 text-sm">
        {spot.registration_deadline}
      </td>
      <td className="p-4">
        <span
          className={`font-display font-bold ${
            isAvailable ? "text-emerald-400" : "text-slate-500"
          }`}
        >
          {spot.spots}
        </span>
      </td>
    </tr>
  );
}

export default function Dashboard({ user, setUser }) {
  const navigate = useNavigate();
  const [availability, setAvailability] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savingAlerts, setSavingAlerts] = useState(false);

  const fetchAvailability = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/availability`);
      setAvailability(response.data);
    } catch (error) {
      console.error("Error fetching availability:", error);
      toast.error("Failed to fetch availability data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAvailability();
    const interval = setInterval(fetchAvailability, 30000);
    return () => clearInterval(interval);
  }, [fetchAvailability]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/availability/refresh`);
      toast.success("Refresh started. Data will update shortly.");
      setTimeout(fetchAvailability, 3000);
    } catch (error) {
      toast.error("Failed to refresh");
    } finally {
      setRefreshing(false);
    }
  };

  const handleAlertToggle = async (value) => {
    if (!user?.telegram_chat_id) {
      toast.error("Please connect Telegram first");
      return;
    }
    
    setSavingAlerts(true);
    try {
      const response = await axios.put(`${API}/users/alerts`, {
        alert_telegram: value
      });
      setUser(response.data);
      toast.success(`Telegram alerts ${value ? "enabled" : "disabled"}`);
    } catch (error) {
      toast.error("Failed to update alert settings");
    } finally {
      setSavingAlerts(false);
    }
  };

  const spots = availability?.spots || [];
  const availableSpots = spots.filter(
    (s) => s.status && s.status.toUpperCase().includes("DISPONIBILI")
  );
  const hasAvailableSpots = availableSpots.length > 0;

  if (loading) {
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
    <div className="min-h-screen bg-background relative">
      {/* Subtle background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="orb w-[400px] h-[400px] bg-emerald-500/10 top-[-5%] right-[10%]" />
        <div className="orb orb-slow w-[300px] h-[300px] bg-cyan-500/8 bottom-[10%] left-[-5%]" style={{ animationDelay: '-7s' }} />
      </div>
      <div className="fixed inset-0 bg-grid-pattern pointer-events-none opacity-50" />

      {/* Header */}
      <nav className="relative z-20 border-b border-slate-800/50 glass">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <div className="relative">
                <div className="w-3 h-3 bg-emerald-400 rounded-full pulse-indicator" />
                <div className="absolute inset-0 w-3 h-3 bg-emerald-400 rounded-full animate-ping opacity-20" />
              </div>
              <span className="font-display text-xl font-bold tracking-tight gradient-text-warm">
                CEnT-S ALERT
              </span>
            </Link>

            <div className="flex items-center gap-3">
              <Link
                to="/history"
                className="flex items-center gap-2 text-slate-400 hover:text-emerald-400 transition-colors rounded-lg px-3 py-2 hover:bg-emerald-500/5"
                data-testid="history-link"
              >
                <History className="w-4 h-4" />
                <span className="hidden sm:inline text-sm">History</span>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <div
            className={`lg:col-span-2 glass-card rounded-xl p-8 animate-fadeIn ${
              hasAvailableSpots
                ? "border-emerald-500/30 neon-glow"
                : ""
            }`}
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div
                    className={`w-4 h-4 rounded-full ${
                      hasAvailableSpots
                        ? "bg-emerald-400 pulse-indicator"
                        : "bg-red-400"
                    }`}
                  />
                  {hasAvailableSpots && (
                    <div className="absolute inset-0 w-4 h-4 bg-emerald-400 rounded-full animate-ping opacity-20" />
                  )}
                </div>
                <h2 className="font-display text-xl font-bold uppercase tracking-wider">
                  CENT@CASA STATUS
                </h2>
              </div>

              <Button
                data-testid="refresh-btn"
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={refreshing}
                className="text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/5 rounded-lg transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? "spinner" : ""}`} />
              </Button>
            </div>

            {hasAvailableSpots ? (
              <div>
                <div className="mb-6">
                  <span className="font-display text-5xl font-bold gradient-text neon-text">
                    {availableSpots.length}
                  </span>
                  <span className="text-slate-400 ml-3 text-lg">
                    SPOT{availableSpots.length !== 1 ? "S" : ""} AVAILABLE
                  </span>
                </div>

                <div className="space-y-3">
                  {availableSpots.map((spot) => (
                    <AvailableSpotCard key={spot.spot_id} spot={spot} />
                  ))}
                </div>

                <a
                  href="https://testcisia.it/studenti_tolc/login_sso.php"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group mt-6 inline-flex items-center gap-2 bg-gradient-to-r from-emerald-400 to-cyan-400 text-slate-900 font-bold px-6 py-3 rounded-xl uppercase tracking-wider transition-all duration-300 hover:shadow-[0_0_30px_rgba(52,211,153,0.3)] hover:-translate-y-0.5"
                  data-testid="book-now-btn"
                >
                  BOOK NOW
                  <ArrowUpRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </a>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <Activity className="w-6 h-6 text-red-400" />
                  <p className="font-display text-3xl sm:text-4xl font-bold text-red-400">
                    NO SPOTS AVAILABLE
                  </p>
                </div>
                <p className="text-slate-400 leading-relaxed">
                  All {availability?.total_cent_casa || 0} CENT@CASA sessions are currently full.
                  We will notify you when spots open.
                </p>
              </div>
            )}

            <div className="mt-6 pt-6 border-t border-slate-800/50 flex items-center gap-2 text-slate-500 text-sm">
              <Clock className="w-4 h-4" />
              <span>
                Last checked:{" "}
                {availability?.timestamp
                  ? new Date(availability.timestamp).toLocaleString()
                  : "Never"}
              </span>
            </div>
          </div>

          {/* Alert Settings Card */}
          <div className="glass-card rounded-xl p-8 animate-fadeIn delay-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 flex items-center justify-center">
                <Bell className="w-5 h-5 text-emerald-400" />
              </div>
              <h2 className="font-display text-lg font-bold uppercase tracking-wider">
                TELEGRAM ALERTS
              </h2>
            </div>

            <div className="space-y-6">
              {user?.telegram_chat_id ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                      <Send className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div>
                      <Label className="text-white">Telegram Connected</Label>
                      <p className="text-slate-500 text-xs">Alerts enabled</p>
                    </div>
                  </div>
                  <Switch
                    data-testid="telegram-alert-toggle"
                    checked={user?.alert_telegram ?? false}
                    onCheckedChange={handleAlertToggle}
                    disabled={savingAlerts}
                    className="data-[state=checked]:bg-emerald-400"
                  />
                </div>
              ) : (
                <div className="space-y-4">
                  <p className="text-slate-400 text-sm leading-relaxed">
                    Connect your Telegram to receive instant alerts when CENT@CASA spots open.
                  </p>
                  <Link
                    to="/setup-telegram"
                    className="group flex items-center justify-center gap-2 bg-gradient-to-r from-sky-500 to-blue-500 text-white font-bold px-6 py-3 rounded-xl uppercase tracking-wider transition-all duration-300 hover:shadow-[0_0_30px_rgba(14,165,233,0.3)] hover:-translate-y-0.5 w-full"
                    data-testid="connect-telegram-btn"
                  >
                    <Send className="w-4 h-4" />
                    Connect Telegram
                  </Link>
                </div>
              )}
            </div>

            <div className="mt-6 pt-6 border-t border-slate-800/50">
              <p className="text-slate-500 text-xs">
                Free instant notifications via Telegram. No SMS charges.
              </p>
            </div>
          </div>

          {/* All Sessions Table */}
          <div className="lg:col-span-3 glass-card rounded-xl p-8 animate-fadeIn delay-200">
            <h2 className="font-display text-lg font-bold uppercase tracking-wider mb-6">
              ALL CENT@CASA SESSIONS
            </h2>

            <div className="overflow-x-auto rounded-lg">
              <table className="w-full table-dark">
                <thead>
                  <tr>
                    <th className="text-left p-4 text-slate-500 font-display text-xs uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left p-4 text-slate-500 font-display text-xs uppercase tracking-wider">
                      University
                    </th>
                    <th className="text-left p-4 text-slate-500 font-display text-xs uppercase tracking-wider">
                      Location
                    </th>
                    <th className="text-left p-4 text-slate-500 font-display text-xs uppercase tracking-wider">
                      Test Date
                    </th>
                    <th className="text-left p-4 text-slate-500 font-display text-xs uppercase tracking-wider">
                      Deadline
                    </th>
                    <th className="text-left p-4 text-slate-500 font-display text-xs uppercase tracking-wider">
                      Spots
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {spots.length > 0 ? (
                    spots.map((spot) => (
                      <SpotTableRow key={spot.spot_id} spot={spot} />
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-500">
                        No data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
