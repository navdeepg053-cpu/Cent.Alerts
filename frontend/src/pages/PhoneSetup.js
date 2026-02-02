import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Phone, ArrowRight, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import PhoneInput from "react-phone-number-input";
import "react-phone-number-input/style.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function PhoneSetup({ user, setUser }) {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!phone) {
      toast.error("Please enter a phone number");
      return;
    }

    setSaving(true);
    try {
      const response = await axios.post(`${API}/users/phone`, { phone });
      setUser(response.data);
      toast.success("Phone number saved successfully!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Error saving phone:", error);
      toast.error("Failed to save phone number");
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
            <div className="w-12 h-12 bg-[#00FF94]/10 border border-[#00FF94]/30 flex items-center justify-center">
              <Phone className="w-6 h-6 text-[#00FF94]" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold">ADD PHONE NUMBER</h1>
              <p className="text-gray-500 text-sm">For SMS & WhatsApp alerts</p>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-gray-400 text-sm uppercase tracking-wider mb-2">
                Phone Number (International)
              </label>
              <PhoneInput
                data-testid="phone-input"
                international
                defaultCountry="IT"
                value={phone}
                onChange={setPhone}
                className="w-full bg-[#050505] border border-[#27272A] p-3 focus-within:border-[#00FF94] focus-within:ring-1 focus-within:ring-[#00FF94] transition-colors"
              />
              <p className="text-gray-500 text-xs mt-2">
                Enter your number with country code. Example: +39 123 456 7890
              </p>
            </div>

            <div className="flex flex-col gap-3">
              <Button
                data-testid="save-phone-btn"
                type="submit"
                disabled={saving || !phone}
                className="w-full bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold rounded-none uppercase tracking-wider py-6 transition-colors hover:shadow-[0_0_20px_rgba(0,255,148,0.4)] disabled:opacity-50"
              >
                {saving ? (
                  <div className="w-5 h-5 border-2 border-black border-t-transparent rounded-full spinner" />
                ) : (
                  <>
                    SAVE & CONTINUE
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>

              <Button
                data-testid="skip-phone-btn"
                type="button"
                onClick={handleSkip}
                variant="ghost"
                className="w-full text-gray-400 hover:text-white font-medium rounded-none uppercase tracking-wider py-6 transition-colors"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                SKIP FOR NOW
              </Button>
            </div>
          </form>

          {/* Info */}
          <div className="mt-8 pt-6 border-t border-[#27272A]">
            <p className="text-gray-500 text-sm">
              Your phone number is used only for sending alerts when CENT@CASA spots
              become available. You can enable or disable SMS and WhatsApp
              notifications from your dashboard.
            </p>
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
