import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import {
  BrainCircuit,
  LogOut,
  Menu,
  X,
  FileText,
  Briefcase,
  Layers,
  Sparkles,
  LayoutDashboard,
  ShieldCheck,
  Search,
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, isAuthenticated, isCandidate, isRecruiter, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/85 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
              HireMinds <span className="text-indigo-400 font-extrabold text-xs uppercase px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">AI</span>
            </span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-1">
          {isAuthenticated ? (
            <>
              {isCandidate && (
                <>
                  <Link
                    to="/candidate/dashboard"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/candidate/dashboard')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <LayoutDashboard className="w-3.5 h-3.5" /> Dashboard
                    </span>
                  </Link>
                  <Link
                    to="/candidate/resumes"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/candidate/resumes')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" /> My Resumes
                    </span>
                  </Link>
                  <Link
                    to="/candidate/jobs"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/candidate/jobs')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5" /> Browse Jobs
                    </span>
                  </Link>
                  <Link
                    to="/candidate/interviews"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/candidate/interviews')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" /> Mock Interviews
                    </span>
                  </Link>
                </>
              )}

              {isRecruiter && (
                <>
                  <Link
                    to="/recruiter/dashboard"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/recruiter/dashboard')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <LayoutDashboard className="w-3.5 h-3.5" /> Dashboard
                    </span>
                  </Link>
                  <Link
                    to="/recruiter/jobs"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/recruiter/jobs')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5" /> Job Postings
                    </span>
                  </Link>
                  <Link
                    to="/recruiter/assessments"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/recruiter/assessments')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5" /> Assessments
                    </span>
                  </Link>
                  <Link
                    to="/jobs"
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive('/jobs')
                        ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-300 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5" /> Explore Jobs
                    </span>
                  </Link>
                </>
              )}
            </>
          ) : (
            <>
              <Link
                to="/jobs"
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
              >
                Browse Jobs
              </Link>
            </>
          )}
        </nav>

        {/* User profile / Auth buttons */}
        <div className="hidden md:flex items-center gap-3">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
              <div className="text-right">
                <div className="text-xs font-medium text-slate-200">{user.full_name}</div>
                <div className="flex items-center justify-end gap-1 mt-0.5">
                  <Badge
                    size="sm"
                    variant={isCandidate ? 'purple' : isRecruiter ? 'cyan' : 'warning'}
                  >
                    {user.role}
                  </Badge>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-slate-400 hover:text-rose-400"
                title="Log out"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                Sign In
              </Button>
              <Button variant="primary" size="sm" onClick={() => navigate('/register')}>
                Get Started
              </Button>
            </div>
          )}
        </div>

        {/* Mobile menu trigger */}
        <div className="md:hidden flex items-center">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-900"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-slate-950 px-4 py-4 space-y-3">
          {isAuthenticated && user ? (
            <>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <p className="text-sm font-semibold text-white">{user.full_name}</p>
                  <p className="text-xs text-slate-400">{user.email}</p>
                </div>
                <Badge variant={isCandidate ? 'purple' : isRecruiter ? 'cyan' : 'warning'}>
                  {user.role}
                </Badge>
              </div>

              {isCandidate && (
                <div className="space-y-1">
                  <Link
                    to="/candidate/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/candidate/resumes"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    My Resumes
                  </Link>
                  <Link
                    to="/candidate/jobs"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    Browse Jobs
                  </Link>
                  <Link
                    to="/candidate/interviews"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    Mock Interviews
                  </Link>
                </div>
              )}

              {isRecruiter && (
                <div className="space-y-1">
                  <Link
                    to="/recruiter/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/recruiter/jobs"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    Job Postings
                  </Link>
                  <Link
                    to="/recruiter/assessments"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900"
                  >
                    Assessments
                  </Link>
                </div>
              )}

              <Button
                variant="danger"
                size="sm"
                className="w-full mt-2"
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
              >
                Sign Out
              </Button>
            </>
          ) : (
            <div className="space-y-2 pt-2">
              <Link
                to="/jobs"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 text-xs font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900 border border-slate-800 text-center"
              >
                Browse All Open Jobs
              </Link>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    navigate('/login');
                  }}
                >
                  Sign In
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    navigate('/register');
                  }}
                >
                  Get Started
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </header>
  );
};
