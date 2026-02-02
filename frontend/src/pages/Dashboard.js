import { useEffect, useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { 
  RefreshCw, 
  LogOut, 
  Bell, 
  Mail, 
  Smartphone, 
  MessageCircle,
  ExternalLink,
  Clock,
  History,
  User,
  Phone
} from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Separate component for available spot card
function AvailableSpotCard({ spot }) {
  return (
    <div className="bg-[#050505] border border-[#00FF94]/30 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-display font-semibold text-white">
            {spot.university}
          </p>
          <p className="text-gray-400 text-sm">
            {spot.city}, {spot.region}
          </p>
        </div>
        <div className="text-right">
          <p className="font-display text-[#00FF94] font-bold">
            {spot.spots} spots
          </p>
          <p className="text-gray-500 text-xs">
            Deadline: {spot.registration_deadline}
          </p>
        </div>
      </div>
    </div>
  );
}

// Separate component for table row
function SpotTableRow({ spot }) {
  const isAvailable = spot.status && spot.status.toUpperCase().includes("DISPONIBILI");
  
  return (
    <tr className="border-b border-[#1A1A1A] hover:bg-[#0F0F0F]">
      <td className="p-4">
        <span
          className={`inline-flex items-center gap-2 px-3 py-1 text-xs font-display uppercase tracking-wider ${
            isAvailable ? "status-available" : "status-full"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isAvailable ? "bg-[#00FF94]" : "bg-[#FF3B30]"
            }`}
          />
          {isAvailable ? "AVAILABLE" : "FULL"}
        </span>
      </td>
      <td className="p-4 font-display text-sm">{spot.university}</td>
      <td className="p-4 text-gray-400 text-sm">
        {spot.city}, {spot.region}
      </td>
      <td className="p-4 font-display text-sm">{spot.test_date}</td>
      <td className="p-4 text-gray-400 text-sm">
        {spot.registration_deadline}
      </td>
      <td className="p-4">
        <span
          className={`font-display font-bold ${
            isAvailable ? "text-[#00FF94]" : "text-gray-500"
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

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`);
      navigate("/");
    } catch (error) {
      console.error("Logout error:", error);
      navigate("/");
    }
  };

  const handleAlertToggle = async (type, value) => {
    setSavingAlerts(true);
    const newSettings = {
      alert_email: type === "email" ? value : user.alert_email,
      alert_sms: type === "sms" ? value : user.alert_sms,
      alert_whatsapp: type === "whatsapp" ? value : user.alert_whatsapp,
    };

    try {
      const response = await axios.put(`${API}/users/alerts`, newSettings);
      setUser(response.data);
      toast.success(`${type.toUpperCase()} alerts ${value ? "enabled" : "disabled"}`);
    } catch (error) {
      toast.error("Failed to update alert settings");
    } finally {
      setSavingAlerts(false);
    }
  };

  // Get available spots
  const spots = availability?.spots || [];
  const availableSpots = spots.filter(
    (s) => s.status && s.status.toUpperCase().includes("DISPONIBILI")
  );
  const hasAvailableSpots = availableSpots.length > 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#00FF94] border-t-transparent rounded-full spinner" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      {/* Header */}
      <nav className="border-b border-[#27272A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-[#00FF94] pulse-indicator" />
              <span className="font-display text-xl font-bold tracking-tight">
                CEnT-S ALERT
              </span>
            </div>

            <div className="flex items-center gap-4">
              <Link
                to="/history"
                className="flex items-center gap-2 text-gray-400 hover:text-white"
                data-testid="history-link"
              >
                <History className="w-4 h-4" />
                <span className="hidden sm:inline text-sm">History</span>
              </Link>

              <div className="flex items-center gap-2 text-gray-400">
                <User className="w-4 h-4" />
                <span className="text-sm hidden sm:inline">{user?.name}</span>
              </div>

              <Button
                data-testid="logout-btn"
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-gray-400 hover:text-white"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <div
            className={`lg:col-span-2 bg-[#0A0A0A] border p-8 animate-fadeIn ${
              hasAvailableSpots
                ? "border-[#00FF94]/50 neon-glow"
                : "border-[#27272A]"
            }`}
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div
                  className={`w-4 h-4 rounded-full ${
                    hasAvailableSpots
                      ? "bg-[#00FF94] pulse-indicator shadow-[0_0_10px_#00FF94]"
                      : "bg-[#FF3B30]"
                  }`}
                />
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
                className="text-gray-400 hover:text-white"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? "spinner" : ""}`} />
              </Button>
            </div>

            {hasAvailableSpots ? (
              <div>
                <div className="mb-6">
                  <span className="font-display text-5xl font-bold text-[#00FF94] neon-text">
                    {availableSpots.length}
                  </span>
                  <span className="text-gray-400 ml-2 text-lg">
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
                  className="mt-6 inline-flex items-center gap-2 bg-[#00FF94] text-black font-bold px-6 py-3 uppercase tracking-wider hover:bg-[#00CC76]"
                  data-testid="book-now-btn"
                >
                  BOOK NOW
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ) : (
              <div>
                <p className="font-display text-4xl font-bold text-[#FF3B30] mb-2">
                  NO SPOTS AVAILABLE
                </p>
                <p className="text-gray-400">
                  All {availability?.total_cent_casa || 0} CENT@CASA sessions are currently full.
                  We will notify you when spots open.
                </p>
              </div>
            )}

            <div className="mt-6 pt-6 border-t border-[#27272A] flex items-center gap-2 text-gray-500 text-sm">
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
          <div className="bg-[#0A0A0A] border border-[#27272A] p-8 animate-fadeIn delay-100">
            <div className="flex items-center gap-3 mb-6">
              <Bell className="w-5 h-5 text-[#00FF94]" />
              <h2 className="font-display text-lg font-bold uppercase tracking-wider">
                ALERT SETTINGS
              </h2>
            </div>

            <div className="space-y-6">
              {/* Email Toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <div>
                    <Label className="text-white">Email Alerts</Label>
                    <p className="text-gray-500 text-xs">{user?.email}</p>
                  </div>
                </div>
                <Switch
                  data-testid="email-alert-toggle"
                  checked={user?.alert_email ?? true}
                  onCheckedChange={(checked) => handleAlertToggle("email", checked)}
                  disabled={savingAlerts}
                  className="data-[state=checked]:bg-[#00FF94]"
                />
              </div>

              {/* SMS Toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Smartphone className="w-4 h-4 text-gray-400" />
                  <div>
                    <Label className="text-white">SMS Alerts</Label>
                    <p className="text-gray-500 text-xs">
                      {user?.phone || "No phone set"}
                    </p>
                  </div>
                </div>
                <Switch
                  data-testid="sms-alert-toggle"
                  checked={user?.alert_sms ?? false}
                  onCheckedChange={(checked) => handleAlertToggle("sms", checked)}
                  disabled={savingAlerts || !user?.phone}
                  className="data-[state=checked]:bg-[#00FF94]"
                />
              </div>

              {/* WhatsApp Toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MessageCircle className="w-4 h-4 text-gray-400" />
                  <div>
                    <Label className="text-white">WhatsApp Alerts</Label>
                    <p className="text-gray-500 text-xs">
                      {user?.phone || "No phone set"}
                    </p>
                  </div>
                </div>
                <Switch
                  data-testid="whatsapp-alert-toggle"
                  checked={user?.alert_whatsapp ?? false}
                  onCheckedChange={(checked) => handleAlertToggle("whatsapp", checked)}
                  disabled={savingAlerts || !user?.phone}
                  className="data-[state=checked]:bg-[#00FF94]"
                />
              </div>

              {!user?.phone && (
                <Link
                  to="/setup-phone"
                  className="flex items-center gap-2 text-[#00FF94] text-sm hover:underline mt-4"
                  data-testid="add-phone-link"
                >
                  <Phone className="w-4 h-4" />
                  Add phone number for SMS/WhatsApp
                </Link>
              )}
            </div>
          </div>

          {/* All Sessions Table */}
          <div className="lg:col-span-3 bg-[#0A0A0A] border border-[#27272A] p-8 animate-fadeIn delay-200">
            <h2 className="font-display text-lg font-bold uppercase tracking-wider mb-6">
              ALL CENT@CASA SESSIONS
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full table-dark">
                <thead>
                  <tr className="bg-[#050505]">
                    <th className="text-left p-4 text-gray-500 font-display text-xs uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left p-4 text-gray-500 font-display text-xs uppercase tracking-wider">
                      University
                    </th>
                    <th className="text-left p-4 text-gray-500 font-display text-xs uppercase tracking-wider">
                      Location
                    </th>
                    <th className="text-left p-4 text-gray-500 font-display text-xs uppercase tracking-wider">
                      Test Date
                    </th>
                    <th className="text-left p-4 text-gray-500 font-display text-xs uppercase tracking-wider">
                      Deadline
                    </th>
                    <th className="text-left p-4 text-gray-500 font-display text-xs uppercase tracking-wider">
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
                      <td colSpan={6} className="p-8 text-center text-gray-500">
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
