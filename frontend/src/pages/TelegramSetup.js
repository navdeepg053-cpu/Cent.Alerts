import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, ArrowRight, ArrowLeft, ExternalLink, Copy, Check } from "lucide-react";
import { toast } from "sonner";

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
    <div className="min-h-screen bg-background flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="orb w-[400px] h-[400px] bg-sky-500/15 top-[10%] right-[-10%]" />
      <div className="orb orb-slow w-[300px] h-[300px] bg-emerald-500/10 bottom-[10%] left-[-5%]" style={{ animationDelay: '-8s' }} />
      <div className="fixed inset-0 bg-grid-pattern pointer-events-none opacity-50" />

      <div className="w-full max-w-md animate-fadeIn relative z-10">
        <div className="glass-card rounded-2xl p-8">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-sky-500/20 to-blue-500/10 border border-sky-500/20 rounded-2xl flex items-center justify-center">
              <Send className="w-7 h-7 text-sky-400" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold gradient-text">CONNECT TELEGRAM</h1>
              <p className="text-slate-500 text-sm">Get instant alerts for free</p>
            </div>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-3 mb-6">
            <div className={`h-1 flex-1 rounded-full transition-colors duration-300 ${step >= 1 ? 'bg-gradient-to-r from-emerald-400 to-cyan-400' : 'bg-slate-800'}`} />
            <div className={`h-1 flex-1 rounded-full transition-colors duration-300 ${step >= 2 ? 'bg-gradient-to-r from-cyan-400 to-indigo-400' : 'bg-slate-800'}`} />
          </div>

          {/* Steps */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="glass rounded-xl p-4">
                <p className="text-slate-400 text-sm mb-4">
                  <span className="text-emerald-400 font-bold">Step 1:</span> Open our Telegram bot
                </p>
                
                {botUsername ? (
                  <a
                    href={`https://t.me/${botUsername}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-center justify-center gap-2 bg-gradient-to-r from-sky-500 to-blue-500 text-white font-bold px-6 py-3 rounded-xl uppercase tracking-wider transition-all duration-300 hover:shadow-[0_0_30px_rgba(14,165,233,0.3)] hover:-translate-y-0.5 w-full"
                    data-testid="open-telegram-btn"
                  >
                    <Send className="w-4 h-4" />
                    Open @{botUsername}
                    <ExternalLink className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </a>
                ) : (
                  <div className="text-center py-3 text-slate-500">Loading bot info...</div>
                )}
              </div>

              <div className="glass rounded-xl p-4">
                <p className="text-slate-400 text-sm mb-4">
                  <span className="text-cyan-400 font-bold">Step 2:</span> Send /start to the bot
                </p>
                
                <button
                  onClick={handleCopyCommand}
                  className="flex items-center justify-between w-full bg-slate-900/50 border border-slate-700/50 px-4 py-3 rounded-lg text-left transition-all duration-300 hover:border-emerald-500/30 hover:bg-emerald-500/5"
                >
                  <code className="font-display text-emerald-400">/start</code>
                  {copied ? (
                    <Check className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <Copy className="w-4 h-4 text-slate-400" />
                  )}
                </button>
              </div>

              <div className="glass rounded-xl p-4">
                <p className="text-slate-400 text-sm mb-2">
                  <span className="text-indigo-400 font-bold">Step 3:</span> The bot will reply with your Chat ID
                </p>
                <p className="text-slate-500 text-xs">
                  It looks like: <code className="text-slate-400 bg-slate-800/50 px-2 py-0.5 rounded">123456789</code>
                </p>
              </div>

              <Button
                onClick={() => setStep(2)}
                className="w-full bg-gradient-to-r from-emerald-400 to-cyan-400 text-slate-900 hover:from-emerald-300 hover:to-cyan-300 font-bold rounded-xl uppercase tracking-wider py-6 transition-all duration-300 hover:shadow-[0_0_30px_rgba(52,211,153,0.3)]"
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
                <label className="block text-slate-400 text-sm uppercase tracking-wider mb-2">
                  Enter Your Chat ID
                </label>
                <Input
                  data-testid="chat-id-input"
                  type="text"
                  value={chatId}
                  onChange={(e) => setChatId(e.target.value)}
                  placeholder="123456789"
                  className="bg-slate-900/50 border-slate-700/50 text-white h-12 font-display rounded-xl focus:border-emerald-400 focus:ring-emerald-400/20"
                />
                <p className="text-slate-500 text-xs mt-2">
                  The number the bot sent you after /start
                </p>
              </div>

              <div className="flex flex-col gap-3">
                <Button
                  data-testid="connect-telegram-btn"
                  type="submit"
                  disabled={saving || !chatId}
                  className="w-full bg-gradient-to-r from-emerald-400 to-cyan-400 text-slate-900 hover:from-emerald-300 hover:to-cyan-300 font-bold rounded-xl uppercase tracking-wider py-6 disabled:opacity-50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(52,211,153,0.3)]"
                >
                  {saving ? (
                    <div className="w-5 h-5 border-2 border-slate-900 border-t-transparent rounded-full spinner" />
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
                  className="w-full text-slate-400 hover:text-white hover:bg-slate-800/50 font-medium rounded-xl uppercase tracking-wider py-6"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  BACK TO INSTRUCTIONS
                </Button>
              </div>
            </form>
          )}

          {/* Skip */}
          <div className="mt-6 pt-6 border-t border-slate-800/50">
            <button
              onClick={handleSkip}
              className="text-slate-500 text-sm hover:text-slate-300 transition-colors w-full text-center"
              data-testid="skip-telegram-btn"
            >
              Skip for now
            </button>
          </div>
        </div>

        {/* User info */}
        <div className="mt-4 text-center">
          <p className="text-slate-500 text-sm">
            Signed in as <span className="text-white">{user?.email}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
