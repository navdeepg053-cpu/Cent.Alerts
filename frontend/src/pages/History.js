import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Bell, Mail, Smartphone, MessageCircle, Clock, Send } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

export default function History({ user }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(`${API}/notifications/history`);
        setNotifications(response.data);
      } catch (error) {
        console.error("Error fetching history:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const getTypeIcon = (type) => {
    switch (type) {
      case "email":
        return <Mail className="w-4 h-4" />;
      case "sms":
        return <Smartphone className="w-4 h-4" />;
      case "whatsapp":
        return <MessageCircle className="w-4 h-4" />;
      case "telegram":
        return <Send className="w-4 h-4" />;
      default:
        return <Bell className="w-4 h-4" />;
    }
  };

  const getTypeBadgeClass = (type) => {
    switch (type) {
      case "email":
        return "bg-sky-500/10 text-sky-400 border-sky-500/20";
      case "sms":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "whatsapp":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "telegram":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

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
      {/* Background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="orb w-[400px] h-[400px] bg-indigo-500/8 top-[10%] right-[-5%]" />
        <div className="orb orb-slow w-[300px] h-[300px] bg-emerald-500/8 bottom-[10%] left-[-5%]" style={{ animationDelay: '-7s' }} />
      </div>
      <div className="fixed inset-0 bg-grid-pattern pointer-events-none opacity-50" />

      {/* Header */}
      <nav className="relative z-20 border-b border-slate-800/50 glass">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-slate-400 hover:text-white hover:bg-slate-800/50 rounded-lg"
                  data-testid="back-btn"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/10 flex items-center justify-center">
                  <Bell className="w-4 h-4 text-indigo-400" />
                </div>
                <span className="font-display text-xl font-bold tracking-tight">
                  NOTIFICATION HISTORY
                </span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="glass-card rounded-xl animate-fadeIn overflow-hidden">
          {notifications.length > 0 ? (
            <div className="divide-y divide-slate-800/30">
              {notifications.map((notification, idx) => (
                <div
                  key={notification.notification_id || idx}
                  className="p-6 hover:bg-emerald-500/[0.02] transition-colors animate-fadeIn opacity-0"
                  style={{ animationDelay: `${idx * 50}ms`, animationFillMode: 'forwards' }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      <div
                        className={`flex items-center gap-2 px-3 py-1.5 border text-xs font-display uppercase tracking-wider rounded-full ${getTypeBadgeClass(
                          notification.type
                        )}`}
                      >
                        {getTypeIcon(notification.type)}
                        {notification.type}
                      </div>

                      <div>
                        <p className="text-white font-medium">
                          {notification.message}
                        </p>
                        {notification.spot_info && (
                          <div className="mt-2 text-sm text-slate-400">
                            <p>
                              <span className="text-slate-500">University:</span>{" "}
                              {notification.spot_info.university}
                            </p>
                            <p>
                              <span className="text-slate-500">Location:</span>{" "}
                              {notification.spot_info.city},{" "}
                              {notification.spot_info.region}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-slate-500 text-sm whitespace-nowrap">
                      <Clock className="w-4 h-4" />
                      <span className="font-display">
                        {new Date(notification.sent_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        notification.status === "sent"
                          ? "bg-emerald-400"
                          : "bg-red-400"
                      }`}
                    />
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-display">
                      {notification.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-slate-700/30 to-slate-800/30 flex items-center justify-center mx-auto mb-5">
                <Bell className="w-8 h-8 text-slate-500" />
              </div>
              <h3 className="font-display text-lg font-semibold text-slate-300 mb-2">
                NO NOTIFICATIONS YET
              </h3>
              <p className="text-slate-500 max-w-md mx-auto leading-relaxed">
                You'll see your notification history here when we send you alerts
                about available CENT@CASA spots.
              </p>
            </div>
          )}
        </div>

        {/* Stats */}
        {notifications.length > 0 && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="glass-card rounded-xl p-6 animate-fadeIn opacity-0" style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}>
              <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">
                Total Notifications
              </p>
              <p className="font-display text-3xl font-bold gradient-text-warm">
                {notifications.length}
              </p>
            </div>
            <div className="glass-card rounded-xl p-6 animate-fadeIn opacity-0" style={{ animationDelay: '300ms', animationFillMode: 'forwards' }}>
              <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">
                Email Alerts
              </p>
              <p className="font-display text-3xl font-bold text-sky-400">
                {notifications.filter((n) => n.type === "email").length}
              </p>
            </div>
            <div className="glass-card rounded-xl p-6 animate-fadeIn opacity-0" style={{ animationDelay: '400ms', animationFillMode: 'forwards' }}>
              <p className="text-slate-500 text-sm uppercase tracking-wider mb-1">
                SMS/WhatsApp
              </p>
              <p className="font-display text-3xl font-bold text-purple-400">
                {
                  notifications.filter(
                    (n) => n.type === "sms" || n.type === "whatsapp"
                  ).length
                }
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
