import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Bell, Mail, Smartphone, MessageCircle, Clock } from "lucide-react";

// Use the backend URL from environment, or empty string for same-origin deployment
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
      default:
        return <Bell className="w-4 h-4" />;
    }
  };

  const getTypeBadgeClass = (type) => {
    switch (type) {
      case "email":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "sms":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "whatsapp":
        return "bg-green-500/10 text-green-400 border-green-500/30";
      default:
        return "bg-gray-500/10 text-gray-400 border-gray-500/30";
    }
  };

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
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-gray-400 hover:text-white"
                  data-testid="back-btn"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-[#00FF94]" />
                <span className="font-display text-xl font-bold tracking-tight">
                  NOTIFICATION HISTORY
                </span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-[#0A0A0A] border border-[#27272A] animate-fadeIn">
          {notifications.length > 0 ? (
            <div className="divide-y divide-[#27272A]">
              {notifications.map((notification, idx) => (
                <div
                  key={notification.notification_id || idx}
                  className="p-6 hover:bg-[#0F0F0F] transition-colors"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      {/* Type Badge */}
                      <div
                        className={`flex items-center gap-2 px-3 py-1 border text-xs font-display uppercase tracking-wider ${getTypeBadgeClass(
                          notification.type
                        )}`}
                      >
                        {getTypeIcon(notification.type)}
                        {notification.type}
                      </div>

                      {/* Content */}
                      <div>
                        <p className="text-white font-medium">
                          {notification.message}
                        </p>
                        {notification.spot_info && (
                          <div className="mt-2 text-sm text-gray-400">
                            <p>
                              <span className="text-gray-500">University:</span>{" "}
                              {notification.spot_info.university}
                            </p>
                            <p>
                              <span className="text-gray-500">Location:</span>{" "}
                              {notification.spot_info.city},{" "}
                              {notification.spot_info.region}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Timestamp */}
                    <div className="flex items-center gap-2 text-gray-500 text-sm whitespace-nowrap">
                      <Clock className="w-4 h-4" />
                      <span className="font-display">
                        {new Date(notification.sent_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Status */}
                  <div className="mt-4 flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        notification.status === "sent"
                          ? "bg-[#00FF94]"
                          : "bg-[#FF3B30]"
                      }`}
                    />
                    <span className="text-xs text-gray-500 uppercase tracking-wider font-display">
                      {notification.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-12 text-center">
              <Bell className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <h3 className="font-display text-lg font-semibold text-gray-400 mb-2">
                NO NOTIFICATIONS YET
              </h3>
              <p className="text-gray-500 max-w-md mx-auto">
                You'll see your notification history here when we send you alerts
                about available CENT@CASA spots.
              </p>
            </div>
          )}
        </div>

        {/* Stats */}
        {notifications.length > 0 && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 animate-fadeIn delay-200">
            <div className="bg-[#0A0A0A] border border-[#27272A] p-6">
              <p className="text-gray-500 text-sm uppercase tracking-wider mb-1">
                Total Notifications
              </p>
              <p className="font-display text-3xl font-bold text-[#00FF94]">
                {notifications.length}
              </p>
            </div>
            <div className="bg-[#0A0A0A] border border-[#27272A] p-6">
              <p className="text-gray-500 text-sm uppercase tracking-wider mb-1">
                Email Alerts
              </p>
              <p className="font-display text-3xl font-bold">
                {notifications.filter((n) => n.type === "email").length}
              </p>
            </div>
            <div className="bg-[#0A0A0A] border border-[#27272A] p-6">
              <p className="text-gray-500 text-sm uppercase tracking-wider mb-1">
                SMS/WhatsApp
              </p>
              <p className="font-display text-3xl font-bold">
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
