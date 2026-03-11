import { useState, useEffect, useRef } from 'react'
import DashboardPage from './pages/DashboardPage.jsx'
import ClaimDetailModal from './pages/ClaimDetailModal.jsx'
import UploadPage from './pages/UploadPage.jsx'
import ExtractionPage from './pages/ExtractionPage.jsx'
import ValidationPage from './pages/ValidationPage.jsx'
import SubmissionPage from './pages/SubmissionPage.jsx'

const STEPS = ['Upload', 'Extraction', 'Validation', 'Submission'];

export default function App() {
  const [view, setView] = useState('dashboard');
  const [step, setStep] = useState(0);
  const [claimData, setClaimData] = useState(null);
  const [validationData, setValidationData] = useState(null);
  const [submissionData, setSubmissionData] = useState(null);
  const [fraudData, setFraudData] = useState(null);
  const [viewingClaimId, setViewingClaimId] = useState(null);

  // UI state
  const [showSettings, setShowSettings] = useState(false);
  const [showAccount, setShowAccount] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('cs-theme') || 'light');
  const accountRef = useRef(null);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cs-theme', theme);
  }, [theme]);

  // Close account menu on outside click
  useEffect(() => {
    function handler(e) {
      if (accountRef.current && !accountRef.current.contains(e.target)) setShowAccount(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  function goToExtraction(data, fraud) {
    setClaimData(data);
    setFraudData(fraud || null);
    setStep(1);
  }
  function goToValidation(data) { setValidationData(data); setStep(2); }
  function goToSubmission(data) { setSubmissionData(data); setStep(3); }

  function goToDashboard() {
    setView('dashboard'); setStep(0);
    setClaimData(null); setValidationData(null);
    setSubmissionData(null); setFraudData(null);
  }

  function startWizard() {
    setView('wizard'); setStep(0);
    setClaimData(null); setValidationData(null);
    setSubmissionData(null); setFraudData(null);
  }

  function handleClaimUpdate(update) { setClaimData(update); }

  return (
    <>
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo" onClick={goToDashboard} style={{ cursor: 'pointer' }}>
            <div className="logo-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            ClaimSense
          </div>
        </div>

        <div className="header-right">
          <button
            className={`header-btn ${showSettings ? 'active' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>

          <div ref={accountRef} style={{ position: 'relative' }}>
            <button className="avatar-btn" onClick={() => setShowAccount(!showAccount)}>
              AD
            </button>
            {showAccount && (
              <div className="account-menu">
                <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>Admin</div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>admin@claimsense.com</div>
                </div>
                <button className="account-menu-item">My Profile</button>
                <button className="account-menu-item">My Claims</button>
                <button className="account-menu-item">Notifications</button>
                <div className="account-divider" />
                <button className="account-menu-item" style={{ color: 'var(--danger)' }}>Sign Out</button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Settings Panel ── */}
      {showSettings && (
        <div className="settings-overlay" onClick={() => setShowSettings(false)}>
          <div className="settings-panel" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-lg)' }}>
              <h3 style={{ margin: 0 }}>Settings</h3>
              <button className="header-btn" onClick={() => setShowSettings(false)} style={{ width: 28, height: 28, fontSize: 13 }}>✕</button>
            </div>

            {/* Appearance */}
            <div className="settings-section">
              <div className="settings-section-title">Appearance</div>
              <div className="settings-row">
                <div className="settings-label">
                  Dark Mode
                  <span>Switch between light and dark theme</span>
                </div>
                <button className={`toggle-switch ${theme === 'dark' ? 'on' : ''}`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} />
              </div>
            </div>

            {/* Notifications */}
            <div className="settings-section">
              <div className="settings-section-title">Notifications</div>
              <div className="settings-row">
                <div className="settings-label">
                  Email Alerts
                  <span>Get notified on claim status changes</span>
                </div>
                <button className="toggle-switch on" />
              </div>
              <div className="settings-row">
                <div className="settings-label">
                  Validation Warnings
                  <span>Show warnings during claim review</span>
                </div>
                <button className="toggle-switch on" />
              </div>
            </div>

            {/* Processing */}
            <div className="settings-section">
              <div className="settings-section-title">Processing</div>
              <div className="settings-row">
                <div className="settings-label">
                  Auto-Validate
                  <span>Run validation after extraction</span>
                </div>
                <button className="toggle-switch" />
              </div>
              <div className="settings-row">
                <div className="settings-label">
                  Fraud Detection
                  <span>Enable document integrity checks</span>
                </div>
                <button className="toggle-switch on" />
              </div>
            </div>

            {/* About */}
            <div className="settings-section">
              <div className="settings-section-title">About</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', lineHeight: 1.7 }}>
                <div>ClaimSense v1.0</div>
                <div>AI-powered claims processing</div>
                <div style={{ marginTop: 8 }}>
                  Built with FastAPI + React
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Main Content ── */}
      <main className="main-content">
        {view === 'dashboard' && (
          <>
            <DashboardPage onRaiseClaim={startWizard} onViewClaim={(id) => setViewingClaimId(id)} />
            {viewingClaimId && (
              <ClaimDetailModal claimId={viewingClaimId} onClose={() => setViewingClaimId(null)} />
            )}
          </>
        )}

        {view === 'wizard' && (
          <>
            <div className="stepper">
              {STEPS.map((label, i) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
                  <div className={`stepper-step ${i === step ? 'active' : ''} ${i < step ? 'completed' : ''}`}>
                    <span className="step-number">{i < step ? '✓' : i + 1}</span>
                    {label}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`stepper-connector ${i < step ? 'completed' : ''}`} />
                  )}
                </div>
              ))}
            </div>

            {step === 0 && <UploadPage onComplete={goToExtraction} />}
            {step === 1 && <ExtractionPage claim={claimData} fraudDetection={fraudData} onComplete={goToValidation} onBack={() => setStep(0)} onClaimUpdate={handleClaimUpdate} />}
            {step === 2 && <ValidationPage claim={claimData} validationData={validationData} onComplete={goToSubmission} onBack={() => setStep(1)} onClaimUpdate={handleClaimUpdate} />}
            {step === 3 && <SubmissionPage submissionData={submissionData} onRestart={goToDashboard} />}
          </>
        )}
      </main>
    </>
  )
}
