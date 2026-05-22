import { useState, useRef } from 'react'
import styles from './App.module.css'

// In Docker: VITE_API_URL is empty → relative URLs → proxied through nginx (no CORS)
// In local dev: VITE_API_URL=http://localhost:8000 → direct call to backend
const API = import.meta.env.VITE_API_URL ?? ''

const ROUTE_META = {
  'Fast-track':         { color: '#16a34a', bg: '#dcfce7', icon: '⚡' },
  'Manual Review':      { color: '#b45309', bg: '#fef3c7', icon: '📋' },
  'Specialist Queue':   { color: '#1d4ed8', bg: '#dbeafe', icon: '🏥' },
  'Investigation Flag': { color: '#dc2626', bg: '#fee2e2', icon: '🚨' },
  'Standard Review':    { color: '#0e7490', bg: '#cffafe', icon: '📁' },
}

const FIELD_LABELS = {
  policyNumber: 'Policy Number',
  policyholderName: 'Policyholder Name',
  effectiveDateStart: 'Effective From',
  effectiveDateEnd: 'Effective To',
  dateOfLoss: 'Date of Loss',
  timeOfLoss: 'Time of Loss',
  location: 'Location',
  description: 'Description',
  claimantName: 'Claimant Name',
  claimantPhone: 'Claimant Phone',
  claimantEmail: 'Claimant Email',
  thirdPartyName: 'Third Party Name',
  thirdPartyPhone: 'Third Party Phone',
  thirdPartyInsurance: 'Third Party Insurance',
  assetType: 'Asset Type',
  assetId: 'Asset ID / VIN',
  assetDescription: 'Vehicle',
  estimatedDamage: 'Estimated Damage',
  claimType: 'Claim Type',
  policeReportFiled: 'Police Report Filed',
  reportNumber: 'Report Number',
  attachments: 'Attachments',
  initialEstimate: 'Initial Estimate',
}

function RouteBadge({ route }) {
  const meta = ROUTE_META[route] || { color: '#4b5563', bg: '#f3f4f6', icon: '📄' }
  return (
    <span
      className={styles.badge}
      style={{ color: meta.color, background: meta.bg, borderColor: meta.color + '40' }}
    >
      {meta.icon} {route}
    </span>
  )
}

function FieldsTable({ fields }) {
  const entries = Object.entries(fields).filter(([, v]) => {
    if (v === null || v === undefined) return false
    if (Array.isArray(v)) return v.length > 0
    return String(v).trim() !== ''
  })

  return (
    <table className={styles.table}>
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <td className={styles.tdLabel}>{FIELD_LABELS[key] || key}</td>
            <td className={styles.tdValue}>
              {Array.isArray(value)
                ? value.join(', ')
                : typeof value === 'number'
                ? key.toLowerCase().includes('damage') || key.toLowerCase().includes('estimate')
                  ? `$${value.toLocaleString()}`
                  : value
                : value}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function App() {
  const [tab, setTab] = useState('upload')   // 'upload' | 'text'
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const dragCounter = useRef(0)
  const [rawText, setRawText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  function handleDrop(e) {
    e.preventDefault()
    dragCounter.current = 0
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLoading(true)

    try {
      let res
      if (tab === 'upload') {
        if (!file) { setError('Please select a file.'); setLoading(false); return }
        const form = new FormData()
        form.append('file', file)
        res = await fetch(`${API}/upload`, { method: 'POST', body: form })
      } else {
        if (!rawText.trim()) { setError('Please paste some FNOL text.'); setLoading(false); return }
        res = await fetch(`${API}/process-text`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: rawText }),
        })
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${res.status}`)
      }
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setResult(null)
    setError(null)
    setFile(null)
    setRawText('')
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className={styles.page}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>⚙</span>
            <span className={styles.logoText}>AssureClaim</span>
          </div>
          <p className={styles.tagline}>Autonomous Insurance Claims Processing Agent</p>
        </div>
      </header>

      <main className={styles.main}>
        {/* ── Input card ── */}
        {!result && (
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>Submit FNOL Document</h2>
            <p className={styles.cardSub}>
              Upload a PDF or TXT file, or paste the raw FNOL text below.
            </p>

            {/* Always-present hidden input — stays in DOM regardless of active tab
                so both the tab label and the dropzone label can activate it */}
            <input
              id="fnol-file"
              ref={fileRef}
              type="file"
              accept=".txt,.pdf"
              style={{ display: 'none' }}
              onChange={e => { setFile(e.target.files[0] || null); setTab('upload') }}
            />

            {/* Tabs */}
            <div className={styles.tabs}>
              <label
                htmlFor="fnol-file"
                className={`${styles.tab} ${tab === 'upload' ? styles.tabActive : ''}`}
                onClick={() => setTab('upload')}
              >
                📎 Upload File
              </label>
              <button
                className={`${styles.tab} ${tab === 'text' ? styles.tabActive : ''}`}
                onClick={() => setTab('text')}
                type="button"
              >
                📝 Paste Text
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {tab === 'upload' ? (
                <label
                  htmlFor="fnol-file"
                  className={`${styles.dropzone} ${dragging ? styles.dropzoneDragging : ''}`}
                  onDragEnter={e => { e.preventDefault(); dragCounter.current++; setDragging(true) }}
                  onDragOver={e => e.preventDefault()}
                  onDragLeave={e => { e.preventDefault(); dragCounter.current--; if (dragCounter.current === 0) setDragging(false) }}
                  onDrop={handleDrop}
                >
                  {file ? (
                    <div className={styles.fileChosen}>
                      <span className={styles.fileIcon}>📄</span>
                      <span className={styles.fileName}>{file.name}</span>
                      <span className={styles.fileSize}>({(file.size / 1024).toFixed(1)} KB)</span>
                      <span className={styles.fileChange}>Click to change</span>
                    </div>
                  ) : (
                    <>
                      <span className={styles.dropIcon}>☁</span>
                      <p className={styles.dropText}>Drag & drop or click to browse</p>
                      <span className={styles.browseBtn}>Browse File</span>
                      <p className={styles.dropHint}>Supports .txt and .pdf</p>
                    </>
                  )}
                </label>
              ) : (
                <textarea
                  className={styles.textarea}
                  placeholder={`Paste FNOL text here...\n\nExample:\nPolicy Number: POL-2024-00123\nPolicyholder Name: James Harrington\n...`}
                  value={rawText}
                  onChange={e => setRawText(e.target.value)}
                  rows={12}
                />
              )}

              {error && <p className={styles.errorMsg}>⚠ {error}</p>}

              <button className={styles.submitBtn} type="submit" disabled={loading}>
                {loading ? <span className={styles.spinner} /> : null}
                {loading ? 'Processing…' : 'Process Claim'}
              </button>
            </form>
          </div>
        )}

        {/* ── Results ── */}
        {result && (
          <div className={styles.results}>
            {/* Route banner */}
            <div
              className={styles.routeBanner}
              style={{
                background: (ROUTE_META[result.recommendedRoute] || {}).bg || '#f3f4f6',
                borderColor: ((ROUTE_META[result.recommendedRoute] || {}).color || '#4b5563') + '50',
              }}
            >
              <div>
                <p className={styles.routeLabel}>Recommended Route</p>
                <RouteBadge route={result.recommendedRoute} />
              </div>
              <button className={styles.resetBtn} onClick={handleReset}>← New Claim</button>
            </div>

            {/* Reasoning */}
            <div className={styles.card}>
              <h3 className={styles.sectionTitle}>Routing Reasoning</h3>
              <p className={styles.reasoning}>{result.reasoning}</p>
            </div>

            {/* Missing fields */}
            {result.missingFields.length > 0 && (
              <div className={`${styles.card} ${styles.missingCard}`}>
                <h3 className={styles.sectionTitle}>⚠ Missing Fields</h3>
                <div className={styles.missingList}>
                  {result.missingFields.map(f => (
                    <span key={f} className={styles.missingTag}>
                      {FIELD_LABELS[f] || f}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted fields */}
            <div className={styles.card}>
              <h3 className={styles.sectionTitle}>Extracted Fields</h3>
              <FieldsTable fields={result.extractedFields} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
