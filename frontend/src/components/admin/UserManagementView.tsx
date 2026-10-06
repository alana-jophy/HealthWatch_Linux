import React, { useState, useEffect } from 'react';
import { fetchSystemUsers, createSystemUser, resetUserPasswordByAdmin } from '../../services/api';
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
  UserPlus,
  KeyRound,
  Eye,
  EyeOff,
  X,
  RotateCcw
} from 'lucide-react';

export const UserManagementView: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Create User Modal State
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newFullName, setNewFullName] = useState<string>('');
  const [newEmail, setNewEmail] = useState<string>('');
  const [newRole, setNewRole] = useState<string>('HEALTH_WORKER');
  const [newPassword, setNewPassword] = useState<string>('');
  const [showNewPassword, setShowNewPassword] = useState<boolean>(false);
  const [addLoading, setAddLoading] = useState<boolean>(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);

  // Admin Reset Password Modal State
  const [resetModalUser, setResetModalUser] = useState<UserItem | null>(null);
  const [tempPassword, setTempPassword] = useState<string>('');
  const [showTempPassword, setShowTempPassword] = useState<boolean>(false);
  const [resetLoading, setResetLoading] = useState<boolean>(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);

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

  const handleOpenAddModal = () => {
    setNewFullName('');
    setNewEmail('');
    setNewRole('HEALTH_WORKER');
    setNewPassword('');
    setShowNewPassword(false);
    setAddError(null);
    setAddSuccess(null);
    setShowAddModal(true);
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFullName.trim()) {
      setAddError('Full name is required.');
      return;
    }
    if (!newEmail.trim()) {
      setAddError('Email address is required.');
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      setAddError('Initial temporary password must be at least 6 characters.');
      return;
    }

    setAddLoading(true);
    setAddError(null);
    setAddSuccess(null);

    try {
      await createSystemUser({
        full_name: newFullName.trim(),
        email: newEmail.trim().toLowerCase(),
        role: newRole,
        password: newPassword,
      });

      setAddSuccess(`User account for ${newEmail} created! They must set a new password upon first login.`);
      await loadUsers();
      setTimeout(() => {
        setShowAddModal(false);
        setAddSuccess(null);
      }, 1800);
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || 'Failed to create system user.');
    } finally {
      setAddLoading(false);
    }
  };

  const handleOpenResetModal = (user: UserItem) => {
    setResetModalUser(user);
    setTempPassword('');
    setShowTempPassword(false);
    setResetError(null);
    setResetSuccess(null);
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetModalUser) return;
    if (!tempPassword || tempPassword.length < 6) {
      setResetError('Temporary password must be at least 6 characters.');
      return;
    }

    setResetLoading(true);
    setResetError(null);
    setResetSuccess(null);

    try {
      await resetUserPasswordByAdmin(resetModalUser.id, tempPassword);
      setResetSuccess(`Temporary password assigned to ${resetModalUser.email}. They will be prompted to reset it on next login.`);
      await loadUsers();
      setTimeout(() => {
        setResetModalUser(null);
        setResetSuccess(null);
      }, 1800);
    } catch (err: any) {
      setResetError(err?.response?.data?.detail || 'Failed to reset password.');
    } finally {
      setResetLoading(false);
    }
  };

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
              Role-Based Access Control (RBAC) governance, authentication accounts, and mandatory first-login password security
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadUsers}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleOpenAddModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            <span>+ Create User</span>
          </button>
        </div>
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
                  <th className="py-3.5 px-4">First-Login Password Policy</th>
                  <th className="py-3.5 px-4">Account Status</th>
                  <th className="py-3.5 px-4">Registered Date</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
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
                      {u.must_change_password ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                          <KeyRound className="w-3 h-3 text-amber-400 shrink-0" />
                          FIRST-LOGIN RESET REQUIRED
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                          PERMANENT PASSWORD SET
                        </span>
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
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleOpenResetModal(u)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-brand-300 hover:text-brand-200 border border-slate-700 text-[11px] font-sans font-semibold transition-colors"
                        title="Assign new temporary password requiring first-login reset"
                      >
                        <RotateCcw className="w-3 h-3 text-brand-400" />
                        <span>Reset Password</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal 1: Create New User */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full rounded-2xl p-6 space-y-5 border border-slate-700 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center">
                  <UserPlus className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Create New Platform User</h3>
                  <p className="text-[11px] text-slate-400">Registers an authenticated health worker, officer, or admin</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {addSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{addSuccess}</span>
              </div>
            )}

            {addError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{addError}</span>
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-300 text-[11px] font-semibold">Full Legal Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Dr. Rajesh Kumar"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 text-[11px] font-semibold">Login Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. rajesh@healthwatch.org"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 text-[11px] font-semibold">Platform Role *</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono"
                >
                  <option value="HEALTH_WORKER">HEALTH_WORKER (Field Surveillance Officer)</option>
                  <option value="PUBLIC_HEALTH_OFFICER">PUBLIC_HEALTH_OFFICER (Lead Epidemiologist)</option>
                  <option value="ADMIN">ADMIN (System Administrator)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 text-[11px] font-semibold">Initial Temporary Password *</label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    placeholder="Enter initial temporary password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-3 py-2 pr-10 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-1"
                    title={showNewPassword ? 'Hide password' : 'Show password'}
                  >
                    {showNewPassword ? <EyeOff className="w-3.5 h-3.5 text-brand-400" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Informative Security Policy Badge */}
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11px] flex items-start gap-2">
                <KeyRound className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  <strong>Mandatory First-Login Policy:</strong> The user will receive this temporary password and will be strictly required to generate a new personal password when they sign in for the first time across either the Web Portal or the Android App.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addLoading}
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {addLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Create User Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Admin Reset Password */}
      {resetModalUser && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-6 space-y-5 border border-slate-700 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
                  <RotateCcw className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Reset Account Password</h3>
                  <p className="text-[11px] text-slate-400">Issue a temporary password requiring first-login change</p>
                </div>
              </div>
              <button
                onClick={() => setResetModalUser(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Target User Info */}
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs">
              <div>
                <span className="font-semibold text-white block">{resetModalUser.full_name}</span>
                <span className="font-mono text-slate-400 text-[11px]">{resetModalUser.email}</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getRoleBadge(resetModalUser.role_name)}`}>
                {resetModalUser.role_name}
              </span>
            </div>

            {resetSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{resetSuccess}</span>
              </div>
            )}

            {resetError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{resetError}</span>
              </div>
            )}

            <form onSubmit={handleResetPasswordSubmit} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-300 text-[11px] font-semibold">New Temporary Password *</label>
                <div className="relative">
                  <input
                    type={showTempPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    placeholder="Enter new temporary password"
                    value={tempPassword}
                    onChange={(e) => setTempPassword(e.target.value)}
                    className="w-full px-3 py-2 pr-10 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowTempPassword(!showTempPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-1"
                    title={showTempPassword ? 'Hide password' : 'Show password'}
                  >
                    {showTempPassword ? <EyeOff className="w-3.5 h-3.5 text-brand-400" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11px] flex items-start gap-2">
                <KeyRound className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  Upon logging in with this temporary password, the user will be blocked from accessing the system until they create their own personal password.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setResetModalUser(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="px-5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {resetLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Assign Temporary Password</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
