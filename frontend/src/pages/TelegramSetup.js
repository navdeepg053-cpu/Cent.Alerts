import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, ArrowRight, ArrowLeft, ExternalLink, Copy, Check } from "lucide-react";
import { toast } from "sonner";

// Use the backend URL from environment, or empty string for same-origin deployment
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

export default function TelegramSetup({ user, setUser }) {
  const navigate = useNavigate();
  const [botUsername, setBotUsername] = useState("");
  const [chatId, setChatId] = useState("");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [step, setStep] = useState(1);

  useEffect(() => {
    // Get bot username
    const fetchBotInfo = async () => {
      try {
        const response = await axios.get(`${API}/telegram/bot-info`);
        setBotUsername(response.data.username);
      } catch (error) {
        console.error("Failed to get bot info:", error);
      }
    };
    fetchBotInfo();
  }, []);

  const handleCopyCommand = () => {
    navigator.clipboard.writeText("/start");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!chatId) {
      toast.error("Please enter your Chat ID");
      return;
    }

    setSaving(true);
    try {
      const response = await axios.post(`${API}/users/telegram`, { chat_id: chatId });
      setUser(response.data);
      toast.success("Telegram connected successfully!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Error connecting Telegram:", error);
      toast.error("Failed to connect Telegram. Check your Chat ID.");
    } finally {
      setSaving(false);
    }
  };

  const handleSkip = () => {
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
      <div className="w-full max-w-md animate-fadeIn">
        <div className="bg-[#0A0A0A] border border-[#27272A] p-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-[#0088cc]/20 border border-[#0088cc]/30 flex items-center justify-center">
              <Send className="w-6 h-6 text-[#0088cc]" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold">CONNECT TELEGRAM</h1>
              <p className="text-gray-500 text-sm">Get instant alerts for free</p>
            </div>
          </div>

          {/* Steps */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="bg-[#050505] border border-[#27272A] p-4">
                <p className="text-gray-400 text-sm mb-4">
                  <span className="text-[#00FF94] font-bold">Step 1:</span> Open our Telegram bot
                </p>
                
                {botUsername ? (
                  <a
                    href={`https://t.me/${botUsername}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 bg-[#0088cc] text-white font-bold px-6 py-3 uppercase tracking-wider hover:bg-[#006699] w-full"
                    data-testid="open-telegram-btn"
                  >
                    <Send className="w-4 h-4" />
                    Open @{botUsername}
                    <ExternalLink className="w-4 h-4" />
                  </a>
                ) : (
                  <div className="text-center py-3 text-gray-500">Loading bot info...</div>
                )}
              </div>

              <div className="bg-[#050505] border border-[#27272A] p-4">
                <p className="text-gray-400 text-sm mb-4">
                  <span className="text-[#00FF94] font-bold">Step 2:</span> Send /start to the bot
                </p>
                
                <button
                  onClick={handleCopyCommand}
                  className="flex items-center justify-between w-full bg-[#1A1A1A] border border-[#27272A] px-4 py-3 text-left hover:border-[#00FF94]/50"
                >
                  <code className="font-display text-[#00FF94]">/start</code>
                  {copied ? (
                    <Check className="w-4 h-4 text-[#00FF94]" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-400" />
                  )}
                </button>
              </div>

              <div className="bg-[#050505] border border-[#27272A] p-4">
                <p className="text-gray-400 text-sm mb-2">
                  <span className="text-[#00FF94] font-bold">Step 3:</span> The bot will reply with your Chat ID
                </p>
                <p className="text-gray-500 text-xs">
                  It looks like: <code className="text-gray-400">123456789</code>
                </p>
              </div>

              <Button
                onClick={() => setStep(2)}
                className="w-full bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold rounded-none uppercase tracking-wider py-6"
                data-testid="got-chat-id-btn"
              >
                I HAVE MY CHAT ID
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          )}

          {step === 2 && (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-gray-400 text-sm uppercase tracking-wider mb-2">
                  Enter Your Chat ID
                </label>
                <Input
                  data-testid="chat-id-input"
                  type="text"
                  value={chatId}
                  onChange={(e) => setChatId(e.target.value)}
                  placeholder="123456789"
                  className="bg-[#050505] border-[#27272A] text-white h-12 font-display focus:border-[#00FF94] focus:ring-[#00FF94]"
                />
                <p className="text-gray-500 text-xs mt-2">
                  The number the bot sent you after /start
                </p>
              </div>

              <div className="flex flex-col gap-3">
                <Button
                  data-testid="connect-telegram-btn"
                  type="submit"
                  disabled={saving || !chatId}
                  className="w-full bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold rounded-none uppercase tracking-wider py-6 disabled:opacity-50"
                >
                  {saving ? (
                    <div className="w-5 h-5 border-2 border-black border-t-transparent rounded-full spinner" />
                  ) : (
                    <>
                      CONNECT TELEGRAM
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </>
                  )}
                </Button>

                <Button
                  type="button"
                  onClick={() => setStep(1)}
                  variant="ghost"
                  className="w-full text-gray-400 hover:text-white font-medium rounded-none uppercase tracking-wider py-6"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  BACK TO INSTRUCTIONS
                </Button>
              </div>
            </form>
          )}

          {/* Skip */}
          <div className="mt-6 pt-6 border-t border-[#27272A]">
            <button
              onClick={handleSkip}
              className="text-gray-500 text-sm hover:text-gray-400 w-full text-center"
              data-testid="skip-telegram-btn"
            >
              Skip for now
            </button>
          </div>
        </div>

        {/* User info */}
        <div className="mt-4 text-center">
          <p className="text-gray-500 text-sm">
            Signed in as <span className="text-white">{user?.email}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
