import { useState, useEffect } from 'react';

export default function DashboardPage({ onRaiseClaim, onViewClaim }) {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { fetchClaims(); }, []);

  async function fetchClaims() {
    try {
      setLoading(true);
      const res = await fetch('/api/claims');
      if (!res.ok) throw new Error('Failed to fetch claims');
      const data = await res.json();
      setClaims(data.claims || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function getStatusBadge(status) {
    const colors = {
      'Extracted': { bg: 'var(--info-bg)', color: 'var(--info)' },
      'Validated': { bg: 'var(--success-bg)', color: 'var(--success)' },
      'Ready for Submission': { bg: 'var(--success-bg)', color: 'var(--success)' },
      'Hold - Action Required': { bg: 'var(--warning-bg)', color: 'var(--warning)' },
      'Submitted': { bg: 'var(--accent-lighter)', color: 'var(--accent)' },
    };
    const s = colors[status] || { bg: 'var(--bg-glass-strong)', color: 'var(--text-muted)' };
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
        padding: '3px 10px', borderRadius: 'var(--radius-pill)',
        fontSize: 'var(--font-size-xs)', fontWeight: 600,
        background: s.bg, color: s.color,
      }}>
        {status}
      </span>
    );
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  function formatCurrency(amount) {
    if (!amount) return '—';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  }

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto' }}>
      {/* Hero */}
      <div style={{
        textAlign: 'center', padding: '40px 24px',
        background: 'var(--bg-glass)',
        borderRadius: 'var(--radius-xl)', marginBottom: 'var(--space-xl)',
        border: '1px solid var(--border)',
      }}>
        <h1 style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px', letterSpacing: '-0.03em' }}>
          Welcome back
        </h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: '20px', fontSize: 'var(--font-size-base)' }}>
          Manage and process insurance claims
        </p>
        <button onClick={onRaiseClaim} className="btn btn-primary" style={{ padding: '12px 30px', fontSize: 'var(--font-size-sm)' }}>
          + New Claim
        </button>
      </div>

      {/* Claims History */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Recent Claims</h2>
          <button onClick={fetchClaims} className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: 'var(--font-size-xs)' }}>
            Refresh
          </button>
        </div>

        {loading && <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>Loading…</p>}
        {error && <p style={{ textAlign: 'center', color: 'var(--danger)', padding: '40px 0' }}>Error: {error}</p>}

        {!loading && !error && claims.length === 0 && (
          <div style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '10px', opacity: 0.5 }}>—</div>
            <p style={{ fontSize: 'var(--font-size-base)' }}>No claims yet</p>
            <p style={{ fontSize: 'var(--font-size-sm)' }}>Click "New Claim" to get started</p>
          </div>
        )}

        {!loading && !error && claims.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0' }}>
              <thead>
                <tr>
                  <th style={thStyle}>Claim ID</th>
                  <th style={thStyle}>Patient</th>
                  <th style={thStyle}>Hospital</th>
                  <th style={thStyle}>Total</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Date</th>
                </tr>
              </thead>
              <tbody>
                {claims.map(claim => (
                  <tr
                    key={claim.id}
                    onClick={() => onViewClaim(claim.id)}
                    style={{ cursor: 'pointer', transition: 'background 0.12s' }}
                    onMouseOver={e => e.currentTarget.style.background = 'var(--accent-lighter)'}
                    onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 600, color: 'var(--accent)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
                        {claim.claim_id}
                      </span>
                    </td>
                    <td style={tdStyle}>{claim.patient_name || '—'}</td>
                    <td style={tdStyle}>{claim.hospital_name || '—'}</td>
                    <td style={tdStyle}>{formatCurrency(claim.total_bill)}</td>
                    <td style={tdStyle}>{getStatusBadge(claim.status)}</td>
                    <td style={tdStyle}>{formatDate(claim.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle = {
  padding: '10px 14px',
  fontSize: 'var(--font-size-xs)',
  fontWeight: 600,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  borderBottom: '1.5px solid var(--border)',
  textAlign: 'left',
};

const tdStyle = {
  padding: '12px 14px',
  fontSize: 'var(--font-size-sm)',
  borderBottom: '1px solid var(--border)',
  color: 'var(--text-primary)',
};
