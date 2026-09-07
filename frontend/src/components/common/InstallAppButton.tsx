import React, { useState, useEffect } from 'react';
import { Download, Smartphone, Check, X, Share, MoreVertical } from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

export const InstallAppButton: React.FC<{ className?: string; variant?: 'header' | 'badge' | 'floating' }> = ({
  className = '',
  variant = 'header',
}) => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isStandalone, setIsStandalone] = useState<boolean>(false);
  const [showInstructions, setShowInstructions] = useState<boolean>(false);
  const [isIOS, setIsIOS] = useState<boolean>(false);

  useEffect(() => {
    // Check if app is already running as standalone PWA
    const isStandaloneMode =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone === true;
    setIsStandalone(isStandaloneMode);

    // Detect iOS
    const userAgent = window.navigator.userAgent.toLowerCase();
    const isIosDevice = /iphone|ipad|ipod/.test(userAgent);
    setIsIOS(isIosDevice);

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    const handleAppInstalled = () => {
      setIsStandalone(true);
      setDeferredPrompt(null);
      setShowInstructions(false);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  // If already running in installed standalone app, do not show button
  if (isStandalone) {
    return null;
  }

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      try {
        await deferredPrompt.prompt();
        const choice = await deferredPrompt.userChoice;
        if (choice.outcome === 'accepted') {
          setDeferredPrompt(null);
        }
      } catch (err) {
        console.error('Install prompt error:', err);
        setShowInstructions(true);
      }
    } else {
      setShowInstructions(true);
    }
  };

  return (
    <>
      {/* Install Button */}
      {variant === 'header' && (
        <button
          onClick={handleInstallClick}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-500/15 hover:bg-brand-500/25 text-brand-300 border border-brand-500/30 text-xs font-semibold transition-all shadow-sm active:scale-95 ${className}`}
          title="Install HealthWatch as an App on your phone"
        >
          <Download className="w-3.5 h-3.5 text-brand-400" />
          <span className="hidden sm:inline">Install App</span>
          <span className="sm:hidden">Install</span>
        </button>
      )}

      {variant === 'badge' && (
        <button
          onClick={handleInstallClick}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all active:scale-95 cursor-pointer ${className}`}
        >
          <Smartphone className="w-4 h-4" />
          <span>Install HealthWatch as App</span>
        </button>
      )}

      {variant === 'floating' && (
        <button
          onClick={handleInstallClick}
          className={`fixed bottom-5 right-5 z-40 flex items-center gap-2 px-4 py-2.5 rounded-full bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold shadow-xl border border-brand-400/40 backdrop-blur-md transition-all active:scale-95 cursor-pointer ${className}`}
        >
          <Download className="w-4 h-4 animate-bounce" />
          <span>Install App</span>
        </button>
      )}

      {/* Instructional Modal when direct prompt is not supported (e.g. iOS Safari, or manual Android Chrome) */}
      {showInstructions && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-6 border border-slate-700 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400">
                  <Smartphone className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Install HealthWatch on Phone</h3>
                  <p className="text-[11px] text-slate-400">Works directly in your mobile browser</p>
                </div>
              </div>
              <button
                onClick={() => setShowInstructions(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Native Android APK Direct Installer */}
            <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-emerald-300">
                <span className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Native Android App Package (.APK):</span>
                </span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  REAL APP (6.8 MB)
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Install as a real Android application with 24/7 background location surveillance foreground service.
              </p>
              <a
                href="/HealthWatch.apk"
                download="HealthWatch.apk"
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg transition-all"
              >
                <Download className="w-4 h-4" />
                <span>Download HealthWatch.apk (Direct Installer)</span>
              </a>
            </div>

            {/* Android Chrome PWA Instructions */}
            <div className={`p-4 rounded-xl border space-y-2.5 ${!isIOS ? 'bg-brand-950/30 border-brand-500/40' : 'bg-slate-900 border-slate-800'}`}>
              <div className="flex items-center gap-2 text-xs font-bold text-brand-300">
                <div className="w-2 h-2 rounded-full bg-brand-400" />
                <span>Or Run Web PWA without APK download:</span>
              </div>
              <ol className="text-xs text-slate-300 space-y-2 list-decimal list-inside leading-relaxed pl-1">
                <li>
                  Tap the <strong className="text-white inline-flex items-center gap-1 font-mono"><MoreVertical className="w-3.5 h-3.5 inline" /> Three Dots</strong> menu at top right.
                </li>
                <li>
                  Tap <strong className="text-white bg-slate-800 px-1.5 py-0.5 rounded font-medium">Install app</strong> or <strong className="text-white bg-slate-800 px-1.5 py-0.5 rounded font-medium">Add to Home screen</strong>.
                </li>
                <li>
                  Tap <strong className="text-brand-400">Install</strong>.
                </li>
              </ol>
            </div>

            {/* iPhone Safari Instructions */}
            <div className={`p-4 rounded-xl border space-y-2.5 ${isIOS ? 'bg-brand-950/30 border-brand-500/40' : 'bg-slate-900 border-slate-800'}`}>
              <div className="flex items-center gap-2 text-xs font-bold text-cyan-300">
                <div className="w-2 h-2 rounded-full bg-cyan-400" />
                <span>On iPhone (Safari):</span>
              </div>
              <ol className="text-xs text-slate-300 space-y-2 list-decimal list-inside leading-relaxed pl-1">
                <li>
                  Tap the <strong className="text-white inline-flex items-center gap-1 font-mono"><Share className="w-3.5 h-3.5 inline" /> Share</strong> button at the bottom of Safari.
                </li>
                <li>
                  Scroll down and tap <strong className="text-white bg-slate-800 px-1.5 py-0.5 rounded font-medium">Add to Home Screen</strong>.
                </li>
                <li>
                  Tap <strong className="text-cyan-400">Add</strong> at top right.
                </li>
              </ol>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowInstructions(false)}
                className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md transition-colors"
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
