import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { 
  Shield, 
  Lock, 
  Mail, 
  ArrowRight, 
  AlertCircle, 
  HelpCircle
} from 'lucide-react';
import { InstallAppButton } from '../common/InstallAppButton';

export const LoginView: React.FC = () => {
  const { login } = useAuth();

  const [identifier, setIdentifier] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = identifier.trim();
    if (!cleanId || !password) {
      setErrorMessage('Please enter both Email / Account ID and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const result = await login(cleanId, password);
    setIsSubmitting(false);

    if (!result.success) {
      setErrorMessage(result.error || 'Invalid credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-8 relative overflow-hidden">
      {/* Background Glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-emerald-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 to-cyan-500 shadow-xl shadow-brand-500/20 border border-brand-400/30 text-white mb-1">
            <Shield className="w-8 h-8" />
          </div>
          <div>
            <h1 className="font-heading text-3xl font-extrabold text-white tracking-tight">
              Health<span className="text-brand-400">Watch</span>
            </h1>
            <p className="text-xs font-mono text-slate-400 uppercase tracking-widest mt-1">
              Epidemiological Surveillance & Patient Telemetry
            </p>
          </div>
        </div>

        {/* Login Form Card */}
        <div className="glass-panel bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
          <div className="mb-6 pb-4 border-b border-slate-800/80 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-200">Secure Sign In</span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              RBAC Protected
            </span>
          </div>

          {errorMessage && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs animate-shake">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <span className="leading-relaxed">{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Email / Account ID
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  required
                  autoCapitalize="none"
                  autoCorrect="off"
                  placeholder="e.g. officer@healthwatch.org or patient email / ID"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all font-mono"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 block">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all font-mono"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 active:scale-[0.99] text-white font-semibold text-sm shadow-lg shadow-brand-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Clean Production Assistance Footer */}
          <div className="mt-6 pt-5 border-t border-slate-800/80 text-center space-y-4">
            <InstallAppButton variant="badge" />
            <p className="text-xs text-slate-400 flex items-center justify-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              <span>Need assistance? Contact Administrator for Account Assistance</span>
            </p>
          </div>
        </div>

        {/* Footer info */}
        <div className="text-center text-[11px] text-slate-500 space-y-1">
          <p>HealthWatch Multi-Role Surveillance Framework &bull; Version 1.0</p>
          <p className="font-mono">FastAPI &bull; PostgreSQL 16 / PostGIS 3.4 &bull; React + Vite</p>
        </div>
      </div>
    </div>
  );
};
