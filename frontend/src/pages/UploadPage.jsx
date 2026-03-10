import { useState, useRef } from 'react'
import { uploadDocument, uploadMultiple, uploadStructured } from '../api.js'

export default function UploadPage({ onComplete }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('pdf'); // 'pdf' or 'form'
  const fileInput = useRef(null);

  // Structured form state
  const [form, setForm] = useState({
    patientName: '', dob: '', gender: 'Male', policyNumber: '',
    hospitalName: '', doctorName: '', department: '',
    diagnosis: '', icd10: '', procedure: '', procedureCode: '',
    admissionType: 'Planned', wardType: 'General', lengthOfStay: '',
    roomCharges: '', icuCharges: '', doctorFees: '', otCharges: '',
    medicines: '', labCharges: '', totalBill: '',
    insurerName: '', preAuthNumber: '',
  });

  function handleFormChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) setFiles(prev => [...prev, ...droppedFiles]);
  }

  function handleFileSelect(e) {
    const selected = Array.from(e.target.files);
    if (selected.length > 0) setFiles(prev => [...prev, ...selected]);
    e.target.value = ''; // reset so same files can be selected again
  }

  function removeFile(index) {
    setFiles(prev => prev.filter((_, i) => i !== index));
  }

  async function handleUploadFiles() {
    if (files.length === 0) return;
    setLoading(true);
    setError('');
    try {
      let result;
      if (files.length === 1) {
        result = await uploadDocument(files[0]);
      } else {
        result = await uploadMultiple(files);
      }
      onComplete(result.claim, result.fraud_detection);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitForm() {
    setLoading(true);
    setError('');
    try {
      const data = {
        patient: {
          name: form.patientName || null,
          dob: form.dob || null,
          gender: form.gender || null,
          policy_number: form.policyNumber || null,
        },
        hospital: {
          name: form.hospitalName || null,
          doctor_name: form.doctorName || null,
          department: form.department || null,
        },
        admission: {
          admission_type: form.admissionType || null,
          ward_type: form.wardType || null,
          length_of_stay: parseInt(form.lengthOfStay) || 0,
        },
        medical: {
          primary_diagnosis: form.diagnosis || null,
          icd10_code: form.icd10 || null,
          procedure: form.procedure || null,
          procedure_code: form.procedureCode || null,
        },
        billing: {
          room_charges: parseFloat(form.roomCharges) || 0,
          icu_charges: parseFloat(form.icuCharges) || 0,
          doctor_fees: parseFloat(form.doctorFees) || 0,
          ot_charges: parseFloat(form.otCharges) || 0,
          medicines: parseFloat(form.medicines) || 0,
          lab_charges: parseFloat(form.labCharges) || 0,
          total_bill: parseFloat(form.totalBill) || 0,
        },
        insurance: {
          insurer_name: form.insurerName || null,
          pre_auth_number: form.preAuthNumber || null,
        },
        documents: {},
      };
      const result = await uploadStructured(data);
      onComplete(result.claim);
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
        <div className="loading-text">
          {mode === 'pdf' ? 'Extracting data from your document...' : 'Processing your claim data...'}
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          This may take a few seconds
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Upload Claim Documents</h1>
        <p>Upload a PDF bill or enter claim details manually</p>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* Mode Toggle */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-xl)' }}>
        <button
          className={`btn ${mode === 'pdf' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setMode('pdf')}
          style={{ padding: '8px 20px', fontSize: 'var(--font-size-sm)' }}
        >
          📄 Upload PDF
        </button>
        <button
          className={`btn ${mode === 'form' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setMode('form')}
          style={{ padding: '8px 20px', fontSize: 'var(--font-size-sm)' }}
        >
          📝 Manual Entry
        </button>
      </div>

      {mode === 'pdf' ? (
        /* File Upload Mode */
        <div>
          <div
            className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
            onClick={() => fileInput.current.click()}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
          >
            <div className="upload-icon">📁</div>
            <h3>Drag & drop your documents here</h3>
            <p>or click to browse — PDF, PNG, JPEG, TIFF supported • <strong>Multiple files OK</strong></p>
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tiff"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>

          {files.length > 0 && (
            <div style={{ marginTop: 'var(--space-md)' }}>
              <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: '8px', color: 'var(--text-secondary)' }}>
                📎 {files.length} file{files.length > 1 ? 's' : ''} selected
              </div>
              {files.map((f, i) => (
                <div key={i} className="file-info" style={{ marginBottom: '6px' }}>
                  <span>{f.type?.includes('pdf') ? '📄' : '🖼️'}</span>
                  <div style={{ flex: 1 }}>
                    <strong>{f.name}</strong>
                    <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
                      {(f.size / 1024).toFixed(1)} KB • {f.type || 'unknown type'}
                    </div>
                  </div>
                  <button
                    className="btn btn-secondary"
                    onClick={() => removeFile(i)}
                    style={{ padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="action-bar">
            <button
              className="btn btn-primary"
              onClick={handleUploadFiles}
              disabled={files.length === 0}
            >
              🚀 Process {files.length > 1 ? `${files.length} Documents` : 'Document'}
            </button>
          </div>
        </div>
      ) : (
        /* Manual Entry Mode */
        <div>
          <div className="card-grid">
            {/* Patient */}
            <div className="card">
              <div className="card-title">👤 Patient Information</div>
              <FormField label="Patient Name" name="patientName" value={form.patientName} onChange={handleFormChange} />
              <FormField label="Date of Birth" name="dob" value={form.dob} onChange={handleFormChange} type="date" />
              <FormSelect label="Gender" name="gender" value={form.gender} onChange={handleFormChange}
                options={['Male', 'Female', 'Other']} />
              <FormField label="Policy Number" name="policyNumber" value={form.policyNumber} onChange={handleFormChange} />
            </div>

            {/* Hospital */}
            <div className="card">
              <div className="card-title">🏥 Hospital Details</div>
              <FormField label="Hospital Name" name="hospitalName" value={form.hospitalName} onChange={handleFormChange} />
              <FormField label="Doctor Name" name="doctorName" value={form.doctorName} onChange={handleFormChange} />
              <FormField label="Department" name="department" value={form.department} onChange={handleFormChange} />
            </div>

            {/* Medical */}
            <div className="card">
              <div className="card-title">🩺 Medical Details</div>
              <FormField label="Primary Diagnosis" name="diagnosis" value={form.diagnosis} onChange={handleFormChange} />
              <FormField label="ICD-10 Code" name="icd10" value={form.icd10} onChange={handleFormChange} placeholder="e.g. I10" />
              <FormField label="Procedure" name="procedure" value={form.procedure} onChange={handleFormChange} />
              <FormField label="Procedure Code" name="procedureCode" value={form.procedureCode} onChange={handleFormChange} />
            </div>

            {/* Admission */}
            <div className="card">
              <div className="card-title">🛏️ Admission</div>
              <FormSelect label="Admission Type" name="admissionType" value={form.admissionType} onChange={handleFormChange}
                options={['Planned', 'Emergency', 'Day Care']} />
              <FormSelect label="Ward Type" name="wardType" value={form.wardType} onChange={handleFormChange}
                options={['General', 'Semi-Private', 'Private', 'ICU']} />
              <FormField label="Length of Stay (days)" name="lengthOfStay" value={form.lengthOfStay} onChange={handleFormChange} type="number" />
            </div>

            {/* Billing */}
            <div className="card">
              <div className="card-title">💰 Billing (₹)</div>
              <FormField label="Room Charges" name="roomCharges" value={form.roomCharges} onChange={handleFormChange} type="number" />
              <FormField label="ICU Charges" name="icuCharges" value={form.icuCharges} onChange={handleFormChange} type="number" />
              <FormField label="Doctor Fees" name="doctorFees" value={form.doctorFees} onChange={handleFormChange} type="number" />
              <FormField label="OT Charges" name="otCharges" value={form.otCharges} onChange={handleFormChange} type="number" />
              <FormField label="Medicines" name="medicines" value={form.medicines} onChange={handleFormChange} type="number" />
              <FormField label="Lab Charges" name="labCharges" value={form.labCharges} onChange={handleFormChange} type="number" />
              <FormField label="Total Bill" name="totalBill" value={form.totalBill} onChange={handleFormChange} type="number" />
            </div>

            {/* Insurance */}
            <div className="card">
              <div className="card-title">🏛️ Insurance</div>
              <FormField label="Insurer Name" name="insurerName" value={form.insurerName} onChange={handleFormChange} />
              <FormField label="Pre-Auth Number" name="preAuthNumber" value={form.preAuthNumber} onChange={handleFormChange} />
            </div>
          </div>

          <div className="action-bar">
            <button className="btn btn-primary" onClick={handleSubmitForm}>
              🚀 Process Claim
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Tiny form components ---- */

function FormField({ label, name, value, onChange, type = 'text', placeholder = '' }) {
  return (
    <div style={{ marginBottom: 'var(--space-md)' }}>
      <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: 500 }}>
        {label}
      </label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          width: '100%',
          padding: '8px 12px',
          background: 'var(--bg-glass-strong)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-sm)',
          outline: 'none',
          transition: 'var(--transition-fast)',
        }}
        onFocus={(e) => e.target.style.borderColor = 'var(--accent-primary)'}
        onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'}
      />
    </div>
  );
}

function FormSelect({ label, name, value, onChange, options }) {
  return (
    <div style={{ marginBottom: 'var(--space-md)' }}>
      <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: 500 }}>
        {label}
      </label>
      <select
        name={name}
        value={value}
        onChange={onChange}
        style={{
          width: '100%',
          padding: '8px 12px',
          background: 'var(--bg-glass-strong)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-sm)',
          outline: 'none',
        }}
      >
        {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    </div>
  );
}
