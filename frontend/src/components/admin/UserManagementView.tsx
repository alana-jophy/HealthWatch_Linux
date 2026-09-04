import React, { useState, useEffect } from 'react';
import { fetchSystemUsers } from '../../services/api';
import { UserItem } from '../../types';
import {
  ShieldCheck,
  User,
  RefreshCw,
  AlertCircle,
  Mail,
  Lock,
  Calendar,
  CheckCircle2,
  XCircle,
  UserPlus
} from 'lucide-react';

export const UserManagementView: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSystemUsers();
      setUsers(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to retrieve system users catalog.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
      case 'PUBLIC_HEALTH_OFFICER':
        return 'bg-brand-500/15 text-brand-400 border-brand-500/30';
      case 'HEALTH_WORKER':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'PATIENT':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">System User Management</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                {users.length} Accounts
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Role-Based Access Control (RBAC) governance, authentication accounts, and privileges
            </p>
          </div>
        </div>

        <button
          onClick={loadUsers}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Users</span>
        </button>
      </div>

      {/* State Handlers */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Retrieving system user accounts...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Failed to Load User Accounts</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadUsers}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : users.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <User className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No System Users Found</h3>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="py-3.5 px-4">Full Name</th>
                  <th className="py-3.5 px-4">Email Address</th>
                  <th className="py-3.5 px-4">System Role</th>
                  <th className="py-3.5 px-4">Superuser</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Registered Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-white">{u.full_name}</td>
                    <td className="py-3.5 px-4 text-brand-300 flex items-center gap-1.5">
                      <Mail className="w-3.5 h-3.5 text-slate-500" />
                      {u.email}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold border ${getRoleBadge(u.role_name)}`}>
                        {u.role_name}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {u.is_superuser ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                          YES (SUPERADMIN)
                        </span>
                      ) : (
                        <span className="text-slate-500">NO</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" /> ACTIVE
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold text-[11px]">
                          <XCircle className="w-3.5 h-3.5" /> DEACTIVATED
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'Initial Seed'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
