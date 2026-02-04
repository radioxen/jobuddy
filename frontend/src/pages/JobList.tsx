import { useState, useEffect, useCallback } from 'react'
import { Check, X, ExternalLink, Star } from 'lucide-react'
import { getJobs, approveJob, rejectJob, approveJobsBatch } from '../api/client'
import { useAppStore } from '../store'
import type { JobListing } from '../types'

export default function JobList() {
  const { jobs, setJobs, totalJobs, setTotalJobs } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('')
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [minScore, setMinScore] = useState<string>('')
  const [selectedJobs, setSelectedJobs] = useState<Set<number>>(new Set())
  const [expandedJob, setExpandedJob] = useState<number | null>(null)
  const [page, setPage] = useState(1)

  const loadJobs = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, per_page: 20 }
      if (filter) params.status = filter
      if (sourceFilter) params.source = sourceFilter
      if (minScore) params.min_score = parseFloat(minScore)

      const result = await getJobs(params)
      setJobs(result.jobs)
      setTotalJobs(result.total)
    } catch (err) {
      console.error('Failed to load jobs', err)
    }
    setLoading(false)
  }, [filter, sourceFilter, minScore, page, setJobs, setTotalJobs])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  const handleApprove = async (id: number) => {
    await approveJob(id)
    loadJobs()
  }

  const handleReject = async (id: number) => {
    await rejectJob(id)
    loadJobs()
  }

  const handleBatchApprove = async () => {
    if (selectedJobs.size === 0) return
    await approveJobsBatch(Array.from(selectedJobs))
    setSelectedJobs(new Set())
    loadJobs()
  }

  const toggleSelect = (id: number) => {
    setSelectedJobs((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (selectedJobs.size === jobs.length) {
      setSelectedJobs(new Set())
    } else {
      setSelectedJobs(new Set(jobs.map((j) => j.id)))
    }
  }

  const getScoreColor = (score: number | null) => {
    if (score === null) return '#999'
    if (score >= 80) return '#4CAF50'
    if (score >= 60) return '#FF9800'
    if (score >= 40) return '#f44336'
    return '#999'
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      discovered: { bg: '#e3f2fd', text: '#1565c0' },
      scored: { bg: '#fff3e0', text: '#e65100' },
      approved: { bg: '#e8f5e9', text: '#2e7d32' },
      applying: { bg: '#fce4ec', text: '#c62828' },
      applied: { bg: '#e8f5e9', text: '#1b5e20' },
      skipped: { bg: '#f5f5f5', text: '#999' },
    }
    const c = colors[status] || { bg: '#f5f5f5', text: '#666' }
    return (
      <span
        style={{
          background: c.bg,
          color: c.text,
          padding: '3px 10px',
          borderRadius: 12,
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {status}
      </span>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Jobs ({totalJobs})</h1>
        {selectedJobs.size > 0 && (
          <button
            onClick={handleBatchApprove}
            style={{
              padding: '8px 16px',
              background: '#4CAF50',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Approve Selected ({selectedJobs.size})
          </button>
        )}
      </div>

      {/* Filters */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 20,
          background: '#fff',
          padding: 16,
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}
      >
        <select
          value={filter}
          onChange={(e) => { setFilter(e.target.value); setPage(1) }}
          style={{ padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }}
        >
          <option value="">All Statuses</option>
          <option value="discovered">Discovered</option>
          <option value="scored">Scored</option>
          <option value="approved">Approved</option>
          <option value="applied">Applied</option>
          <option value="skipped">Skipped</option>
        </select>
        <select
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(1) }}
          style={{ padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }}
        >
          <option value="">All Sources</option>
          <option value="indeed">Indeed</option>
          <option value="linkedin">LinkedIn</option>
        </select>
        <input
          type="number"
          placeholder="Min Score"
          value={minScore}
          onChange={(e) => { setMinScore(e.target.value); setPage(1) }}
          style={{ padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, width: 120 }}
        />
        <button
          onClick={loadJobs}
          style={{
            padding: '8px 16px',
            background: '#1a1a2e',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <p style={{ color: '#666', textAlign: 'center', padding: 40 }}>Loading jobs...</p>
      ) : jobs.length === 0 ? (
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
          No jobs found. Start a search from the Dashboard.
        </div>
      ) : (
        <>
          {/* Select all */}
          <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>
            <label style={{ cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={selectedJobs.size === jobs.length && jobs.length > 0}
                onChange={selectAll}
                style={{ marginRight: 6 }}
              />
              Select all on this page
            </label>
          </div>

          {/* Job cards */}
          {jobs.map((job) => (
            <div
              key={job.id}
              style={{
                background: '#fff',
                borderRadius: 12,
                padding: 16,
                marginBottom: 12,
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                border: selectedJobs.has(job.id) ? '2px solid #4CAF50' : '2px solid transparent',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <input
                  type="checkbox"
                  checked={selectedJobs.has(job.id)}
                  onChange={() => toggleSelect(job.id)}
                  style={{ marginTop: 4 }}
                />

                {/* Score badge */}
                <div
                  style={{
                    minWidth: 50,
                    height: 50,
                    borderRadius: '50%',
                    background: getScoreColor(job.fit_score),
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: 16,
                  }}
                >
                  {job.fit_score !== null ? Math.round(job.fit_score) : '?'}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3
                      style={{ fontSize: 16, fontWeight: 600, cursor: 'pointer' }}
                      onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                    >
                      {job.title}
                    </h3>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      {getStatusBadge(job.status)}
                      <span
                        style={{
                          fontSize: 11,
                          color: '#999',
                          background: '#f5f5f5',
                          padding: '3px 8px',
                          borderRadius: 12,
                          textTransform: 'uppercase',
                        }}
                      >
                        {job.source}
                      </span>
                    </div>
                  </div>

                  <p style={{ fontSize: 14, color: '#666', marginTop: 4 }}>
                    {job.company} — {job.location}
                    {job.salary_info && ` — ${job.salary_info}`}
                  </p>

                  {job.fit_reasoning && (
                    <p style={{ fontSize: 13, color: '#888', marginTop: 4, fontStyle: 'italic' }}>
                      {job.fit_reasoning}
                    </p>
                  )}

                  {expandedJob === job.id && (
                    <div
                      style={{
                        marginTop: 12,
                        padding: 12,
                        background: '#f8f9fa',
                        borderRadius: 8,
                        fontSize: 13,
                        lineHeight: 1.6,
                        maxHeight: 300,
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {job.description}
                    </div>
                  )}

                  <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                    {job.status !== 'approved' && job.status !== 'skipped' && (
                      <>
                        <button
                          onClick={() => handleApprove(job.id)}
                          style={{
                            padding: '6px 14px',
                            background: '#4CAF50',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: 13,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Check size={14} /> Approve
                        </button>
                        <button
                          onClick={() => handleReject(job.id)}
                          style={{
                            padding: '6px 14px',
                            background: '#f5f5f5',
                            color: '#666',
                            border: '1px solid #ddd',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: 13,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <X size={14} /> Skip
                        </button>
                      </>
                    )}
                    <a
                      href={job.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: '6px 14px',
                        background: '#e3f2fd',
                        color: '#1565c0',
                        border: 'none',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 13,
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <ExternalLink size={14} /> View
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination */}
          {totalJobs > 20 && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 20 }}>
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                style={{
                  padding: '8px 16px',
                  border: '1px solid #ddd',
                  borderRadius: 8,
                  background: '#fff',
                  cursor: page === 1 ? 'default' : 'pointer',
                  opacity: page === 1 ? 0.5 : 1,
                }}
              >
                Previous
              </button>
              <span style={{ padding: '8px 0', color: '#666' }}>
                Page {page} of {Math.ceil(totalJobs / 20)}
              </span>
              <button
                disabled={page * 20 >= totalJobs}
                onClick={() => setPage(page + 1)}
                style={{
                  padding: '8px 16px',
                  border: '1px solid #ddd',
                  borderRadius: 8,
                  background: '#fff',
                  cursor: page * 20 >= totalJobs ? 'default' : 'pointer',
                  opacity: page * 20 >= totalJobs ? 0.5 : 1,
                }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
