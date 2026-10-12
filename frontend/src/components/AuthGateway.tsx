import React, { useState } from 'react';
import {
  GraduationCap,
  Sparkles,
  Database,
  ShieldCheck,
  Lock,
  Mail,
  User as UserIcon,
  ArrowRight
} from 'lucide-react';

interface AuthGatewayProps {
  onLogin: (credentials: { email: string; password: string }) => Promise<void>;
  onRegister: (data: { email: string; password: string; full_name: string; role: string }) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export const AuthGateway: React.FC<AuthGatewayProps> = ({
  onLogin,
  onRegister,
  loading,
  error,
}) => {
  const [authMode, setAuthMode] = useState<'LOGIN' | 'REGISTER'>('LOGIN');
  const [email, setEmail] = useState('alex@student.univ.edu');
  const [password, setPassword] = useState('Password123!');
  const [fullName, setFullName] = useState('');
  const [selectedRole, setSelectedRole] = useState('STUDENT');

  const demoAccounts = [
    {
      role: 'Student Demo',
      name: 'Alex Rivera',
      email: 'alex@student.univ.edu',
      pw: 'Password123!',
      color: '#15803d',
    },
    {
      role: 'Faculty Demo',
      name: 'Prof. Alan Turing',
      email: 'prof.alan@univ.edu',
      pw: 'Password123!',
      color: '#1e3a8a',
    },
    {
      role: 'Admin Demo',
      name: 'Dean Victoria Vance',
      email: 'admin@univ.edu',
      pw: 'AdminPass123!',
      color: '#b91c1c',
    },
  ];

  const handleSelectDemo = (acc: typeof demoAccounts[0]) => {
    setEmail(acc.email);
    setPassword(acc.pw);
    setAuthMode('LOGIN');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (authMode === 'LOGIN') {
      onLogin({ email, password });
    } else {
      onRegister({ email, password, full_name: fullName, role: selectedRole });
    }
  };

  return (
    <div className="auth-page-wrapper">
      <div className="auth-split-card">
        {/* Left: Brand Column */}
        <div className="auth-brand-col">
          <div>
            <div className="auth-brand-header">
              <div className="auth-brand-crest">
                <GraduationCap size={26} color="#ffffff" />
              </div>
              <div>
                <h1 className="auth-brand-title">Apex Academic</h1>
                <div className="auth-brand-sub">University Learning Management System</div>
              </div>
            </div>

            <div className="auth-brand-body">
              <div className="auth-brand-headline">
                State-of-the-Art Academic Workspace with Grounded AI Intelligence
              </div>

              <div className="auth-brand-features">
                <div className="auth-feature-row">
                  <div className="auth-feature-icon">
                    <Database size={13} />
                  </div>
                  <span>
                    <strong>Polyglot Distributed Architecture:</strong> PostgreSQL transactions, pgvector high-dimensional embeddings, MongoDB announcements, and Redis.
                  </span>
                </div>

                <div className="auth-feature-row">
                  <div className="auth-feature-icon">
                    <Sparkles size={13} />
                  </div>
                  <span>
                    <strong>Curriculum-Grounded AI:</strong> Semantic question answering over DSA, OS, Embedded Systems, Japanese, and ML notes.
                  </span>
                </div>

                <div className="auth-feature-row">
                  <div className="auth-feature-icon">
                    <ShieldCheck size={13} />
                  </div>
                  <span>
                    <strong>Role-Based Access Control:</strong> Strict academic boundaries for Students, Faculty, and University Administrators.
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="auth-brand-footer">
            <span>Spring 2026 Academic Term</span>
            <span>Version 2.0.0 Production</span>
          </div>
        </div>

        {/* Right: Interactive Authentication Form */}
        <div className="auth-form-col">
          <div>
            <div className="auth-tabs-toggle">
              <button
                className={`auth-tab-btn ${authMode === 'LOGIN' ? 'active' : ''}`}
                onClick={() => setAuthMode('LOGIN')}
              >
                Sign In
              </button>
              <button
                className={`auth-tab-btn ${authMode === 'REGISTER' ? 'active' : ''}`}
                onClick={() => setAuthMode('REGISTER')}
              >
                Create Account
              </button>
            </div>

            {error && (
              <div className="banner-alert banner-alert-error" style={{ marginBottom: '16px' }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {authMode === 'REGISTER' && (
                <>
                  <div className="form-group" style={{ marginBottom: '0' }}>
                    <label className="form-label">Full Name</label>
                    <div style={{ position: 'relative' }}>
                      <input
                        type="text"
                        className="form-input"
                        style={{ width: '100%', paddingLeft: '34px' }}
                        required
                        placeholder="e.g. John Doe"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                      />
                      <UserIcon size={14} color="#94a3b8" style={{ position: 'absolute', left: '11px', top: '12px' }} />
                    </div>
                  </div>

                  <div className="form-group" style={{ marginBottom: '0' }}>
                    <label className="form-label">Role</label>
                    <select
                      className="form-select"
                      value={selectedRole}
                      onChange={(e) => setSelectedRole(e.target.value)}
                    >
                      <option value="STUDENT">Student</option>
                      <option value="TEACHER">Faculty / Teacher</option>
                    </select>
                  </div>
                </>
              )}

              <div className="form-group" style={{ marginBottom: '0' }}>
                <label className="form-label">University Email</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="email"
                    className="form-input"
                    style={{ width: '100%', paddingLeft: '34px' }}
                    required
                    placeholder="student@univ.edu"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Mail size={14} color="#94a3b8" style={{ position: 'absolute', left: '11px', top: '12px' }} />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: '0' }}>
                <label className="form-label">Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="password"
                    className="form-input"
                    style={{ width: '100%', paddingLeft: '34px' }}
                    required
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <Lock size={14} color="#94a3b8" style={{ position: 'absolute', left: '11px', top: '12px' }} />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
                style={{ marginTop: '8px', padding: '10px 16px', fontWeight: 600 }}
              >
                {loading ? (
                  <span className="spinner" />
                ) : (
                  <>
                    <span>{authMode === 'LOGIN' ? 'Sign in to Portal' : 'Register Account'}</span>
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Quick Demo Credentials Autofill */}
          <div className="demo-credentials-section">
            <div className="demo-title-row">
              <span className="demo-title-text">One-Click Test Accounts</span>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Click to autofill</span>
            </div>

            <div className="demo-accounts-grid">
              {demoAccounts.map((acc, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="demo-account-card"
                  onClick={() => handleSelectDemo(acc)}
                >
                  <div className="demo-account-info">
                    <div className="demo-account-avatar" style={{ backgroundColor: acc.color }}>
                      {acc.name.charAt(0)}
                    </div>
                    <div>
                      <div className="demo-account-name">{acc.name}</div>
                      <div className="demo-account-email">{acc.email}</div>
                    </div>
                  </div>
                  <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
                    {acc.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
