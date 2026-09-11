import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in HealthWatch component tree:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-8">
          <div className="max-w-md w-full glass-panel bg-slate-900/90 border border-rose-500/30 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-5 text-center">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-white">Application Render Notice</h2>
              <p className="text-xs text-slate-400 mt-1">
                A component encountered an unexpected runtime state.
              </p>
            </div>
            {this.state.error?.message && (
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-rose-300 font-mono text-[11px] text-left break-words">
                {this.state.error.message}
              </div>
            )}
            <button
              onClick={this.handleReset}
              className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white font-semibold text-xs transition-all shadow-md active:scale-98 cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Reload HealthWatch</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
