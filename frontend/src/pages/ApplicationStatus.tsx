import { useState, useEffect, useCallback } from 'react'
import { FileText, Download, Play, RefreshCw } from 'lucide-react'
import {
  getApplications,
  prepareDocuments,
  fillForm,
  prepareAllApproved,
  downloadResume,
  downloadCoverLetter,
} from '../api/client'
import { useAppStore } from '../store'
import type { Application } from '../types'

const STATUS_ORDER = [
  'pending',
  'documents_ready',
  'form_filled',
  'awaiting_review',
  'submitted',
  'failed',
]

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  documents_ready: 'Docs Ready',
  form_filled: 'Form Filled',
  awaiting_review: 'Awaiting Review',
  submitted: 'Submitted',
  failed: 'Failed',
}

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  pending: { bg: '#fff3e0', text: '#e65100', border: '#ffcc80' },
  documents_ready: { bg: '#e3f2fd', text: '#1565c0', border: '#90caf9' },
  form_filled: { bg: '#f3e5f5', text: '#7b1fa2', border: '#ce93d8' },
  awaiting_review: { bg: '#fce4ec', text: '#c62828', border: '#ef9a9a' },
  submitted: { bg: '#e8f5e9', text: '#2e7d32', border: '#a5d6a7' },
  failed: { bg: '#ffebee', text: '#b71c1c', border: '#ef9a9a' },
}

export default function ApplicationStatus() {
  const { applications, setApplications } = useAppStore()
  const [loading, setLoading] = useState(false)

  const loadApplications = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getApplications()
      setApplications(result.applications)
    } catch (err) {
      console.error('Failed to load applications', err)
    }
    setLoading(false)
  }, [setApplications])

  useEffect(() => {
    loadApplications()
  }, [loadApplications])

  const handlePrepare = async (appId: number) => {
    try {
      await prepareDocuments(appId)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to prepare documents')
    }
  }

  const handleFillForm = async (appId: number) => {
    try {
      await fillForm(appId)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to fill form')
    }
  }

  const handlePrepareAll = async () => {
    try {
      await prepareAllApproved()
    } catch (err: any) {
      alert('Failed to start batch preparation')
    }
  }

  // Group applications by status
  const grouped: Record<string, Application[]> = {}
  for (const status of STATUS_ORDER) {
    grouped[status] = applications.filter((a) => a.status === status)
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Applications ({applications.length})</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handlePrepareAll}
            style={{
              padding: '8px 16px',
              background: '#1a1a2e',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: 13,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <FileText size={14} /> Prepare All Docs
          </button>
          <button
            onClick={loadApplications}
            style={{
              padding: '8px 16px',
              background: '#fff',
              color: '#333',
              border: '1px solid #ddd',
              borderRadius: 8,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: '#666', textAlign: 'center', padding: 40 }}>Loading...</p>
      ) : applications.length === 0 ? (
        <div
          style={{
            background: '#fff',
            borderRadius: 12,
            padding: 40,
            textAlign: 'center',
            color: '#666',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          No applications yet. Approve some jobs first.
        </div>
      ) : (
        /* Kanban-style columns */
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${STATUS_ORDER.filter((s) => grouped[s].length > 0).length}, 1fr)`,
            gap: 16,
            minHeight: 400,
          }}
        >
          {STATUS_ORDER.filter((status) => grouped[status].length > 0).map((status) => {
            const colors = STATUS_COLORS[status] || STATUS_COLORS.pending
            return (
              <div key={status}>
                <div
                  style={{
                    background: colors.bg,
                    border: `1px solid ${colors.border}`,
                    borderRadius: 8,
                    padding: '8px 12px',
                    marginBottom: 12,
                    fontWeight: 600,
                    fontSize: 13,
                    color: colors.text,
                    textAlign: 'center',
                  }}
                >
                  {STATUS_LABELS[status]} ({grouped[status].length})
                </div>

                {grouped[status].map((app) => (
                  <div
                    key={app.id}
                    style={{
                      background: '#fff',
                      borderRadius: 10,
                      padding: 14,
                      marginBottom: 10,
                      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                      borderLeft: `3px solid ${colors.border}`,
                    }}
                  >
                    <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                      {app.job?.title || `Job #${app.job_id}`}
                    </h4>
                    <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                      {app.job?.company} — {app.job?.location}
                    </p>

                    {app.error_message && (
                      <p style={{ fontSize: 12, color: '#c62828', marginBottom: 8 }}>
                        Error: {app.error_message}
                      </p>
                    )}

                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {status === 'pending' && (
                        <button
                          onClick={() => handlePrepare(app.id)}
                          style={{
                            padding: '4px 10px',
                            background: '#1a1a2e',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: 12,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <FileText size={12} /> Prepare
                        </button>
                      )}

                      {status === 'documents_ready' && (
                        <button
                          onClick={() => handleFillForm(app.id)}
                          style={{
                            padding: '4px 10px',
                            background: '#4CAF50',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: 12,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Play size={12} /> Fill Form
                        </button>
                      )}

                      {app.tailored_resume_path && (
                        <a
                          href={downloadResume(app.id)}
                          style={{
                            padding: '4px 10px',
                            background: '#e3f2fd',
                            color: '#1565c0',
                            borderRadius: 6,
                            fontSize: 12,
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Download size={12} /> Resume
                        </a>
                      )}

                      {app.cover_letter_path && (
                        <a
                          href={downloadCoverLetter(app.id)}
                          style={{
                            padding: '4px 10px',
                            background: '#f3e5f5',
                            color: '#7b1fa2',
                            borderRadius: 6,
                            fontSize: 12,
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Download size={12} /> Cover Letter
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
