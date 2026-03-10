import { useState, useEffect } from 'react'
import { validatePolicyDemo } from '../api.js'

export default function ValidationPage({ claim, validationData, onComplete, onBack }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(validationData);

  useEffect(() => {
    if (!results && claim) {
      runValidation();
    }
  }, []);

  async function runValidation() {
    setLoading(true);
    setError('');
    try {
      const data = await validatePolicyDemo(claim);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <div className="loading-text">Running policy validation rules...</div>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Checking 8 deterministic rules
        </p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="page-header">
        <h1>Policy Validation</h1>
        {error && <div className="error-banner">⚠️ {error}</div>}
        <button className="btn btn-primary" onClick={runValidation}>🔄 Retry Validation</button>
      </div>
    );
  }

  const passCount = results.validation_results?.filter(r => r.status === 'PASS').length || 0;
  const failCount = results.validation_results?.filter(r => r.status === 'FAIL').length || 0;
  const warnCount = results.validation_results?.filter(r => r.status === 'WARNING').length || 0;
  const totalBill = claim?.billing?.total_bill || 0;

  // Calculate patient vs insurer liability from copay result
  const copayResult = results.validation_results?.find(r => r.rule === 'copay');
  const patientPays = copayResult?.amount || 0;
  const insurerPays = totalBill - patientPays;

  return (
    <div>
      <div className="page-header">
        <h1>Policy Validation Results</h1>
        <p>
          Using{' '}
          <strong style={{ color: 'var(--accent-primary)' }}>
            {results.policy_rules?.insurer || 'Demo Policy'}
          </strong>
          {' '}• Sum Insured: ₹{(results.policy_rules?.sum_insured || 0).toLocaleString('en-IN')}
        </p>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* Summary Stats */}
      <div style={{ display: 'flex', gap: 'var(--space-md)', justifyContent: 'center', marginBottom: 'var(--space-xl)', flexWrap: 'wrap' }}>
        <StatBadge label="Passed" count={passCount} color="var(--success)" bg="var(--success-bg)" />
        <StatBadge label="Failed" count={failCount} color="var(--danger)" bg="var(--danger-bg)" />
        <StatBadge label="Warnings" count={warnCount} color="var(--warning)" bg="var(--warning-bg)" />
      </div>

      {/* Overall Status */}
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-xl)' }}>
        <span className={`badge ${results.overall_status === 'PASS' ? 'badge-pass' : results.overall_status === 'FAIL' ? 'badge-fail' : 'badge-warning'}`}
          style={{ fontSize: 'var(--font-size-sm)', padding: '6px 16px' }}>
          Overall: {results.overall_status}
        </span>
      </div>

      {/* Validation Rules */}
      <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
        <div className="card-title">📋 Rule-by-Rule Results</div>
        <div className="validation-list">
          {results.validation_results?.map((r, i) => (
            <div key={i} className="validation-item">
              <span className={`badge badge-${r.status.toLowerCase()}`}>
                {r.status === 'PASS' ? '✓' : r.status === 'FAIL' ? '✗' : '⚠'} {r.status}
              </span>
              <span className="rule-name">{formatRuleName(r.rule)}</span>
              <span className="rule-reason">{r.reason}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Liability Breakdown */}
      <div className="card-grid" style={{ marginBottom: 'var(--space-lg)' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
            Insurer Pays
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--success)' }}>
            ₹{insurerPays.toLocaleString('en-IN')}
          </div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
            Patient Pays
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--warning)' }}>
            ₹{patientPays.toLocaleString('en-IN')}
          </div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
            Total Bill
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color: 'var(--accent-primary)' }}>
            ₹{totalBill.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Coverage Summary */}
      {results.coverage_summary && (
        <div className="card">
          <div className="card-title">📝 Coverage Summary</div>
          <div className="summary-box">
            {results.coverage_summary.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        </div>
      )}

      <div className="action-bar">
        <button className="btn btn-secondary" onClick={onBack}>← Back</button>
        <button className="btn btn-primary" onClick={() => onComplete(results)}>
          Proceed to Final Check →
        </button>
      </div>
    </div>
  );
}

function StatBadge({ label, count, color, bg }) {
  return (
    <div style={{
      background: bg,
      border: `1px solid ${color}30`,
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-md) var(--space-xl)',
      textAlign: 'center',
      minWidth: '120px',
    }}>
      <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700, color }}>{count}</div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>{label}</div>
    </div>
  );
}

function formatRuleName(rule) {
  return rule
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}
