import { useState } from 'react'
import UploadPage from './pages/UploadPage.jsx'
import ExtractionPage from './pages/ExtractionPage.jsx'
import ValidationPage from './pages/ValidationPage.jsx'
import SubmissionPage from './pages/SubmissionPage.jsx'

const STEPS = ['Upload', 'Extraction', 'Validation', 'Submission'];

export default function App() {
  const [step, setStep] = useState(0);
  const [claimData, setClaimData] = useState(null);
  const [validationData, setValidationData] = useState(null);
  const [submissionData, setSubmissionData] = useState(null);

  function goToExtraction(data) {
    setClaimData(data);
    setStep(1);
  }

  function goToValidation(data) {
    setValidationData(data);
    setStep(2);
  }

  function goToSubmission(data) {
    setSubmissionData(data);
    setStep(3);
  }

  function restart() {
    setStep(0);
    setClaimData(null);
    setValidationData(null);
    setSubmissionData(null);
  }

  return (
    <>
      <header className="app-header">
        <div className="app-logo" onClick={restart} style={{ cursor: 'pointer' }}>
          <div className="logo-icon">🛡️</div>
          ClaimSense<span className="logo-dot">.ai</span>
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Smart Claims Processing
        </span>
      </header>

      <main className="main-content">
        {/* Stepper */}
        <div className="stepper">
          {STEPS.map((label, i) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
              <div
                className={`stepper-step ${i === step ? 'active' : ''} ${i < step ? 'completed' : ''}`}
              >
                <span className="step-number">
                  {i < step ? '✓' : i + 1}
                </span>
                {label}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`stepper-connector ${i < step ? 'completed' : ''}`} />
              )}
            </div>
          ))}
        </div>

        {/* Pages */}
        {step === 0 && <UploadPage onComplete={goToExtraction} />}
        {step === 1 && <ExtractionPage claim={claimData} onComplete={goToValidation} onBack={() => setStep(0)} />}
        {step === 2 && <ValidationPage claim={claimData} validationData={validationData} onComplete={goToSubmission} onBack={() => setStep(1)} />}
        {step === 3 && <SubmissionPage submissionData={submissionData} onRestart={restart} />}
      </main>
    </>
  )
}
