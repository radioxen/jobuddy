import { useState, useEffect, useCallback } from 'react'
import { Upload, Settings, Search, Monitor } from 'lucide-react'
import {
  uploadResume,
  getProfile,
  updatePreferences,
  searchJobs,
  startBrowser,
  getBrowserStatus,
  openLogin,
} from '../api/client'
import { useAppStore } from '../store'
import type { UserProfile, UserPreferences } from '../types'

export default function Dashboard() {
  const { user, setUser, setIsSearching } = useAppStore()
  const [uploading, setUploading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [browserStatus, setBrowserStatus] = useState<Record<string, any>>({})
  const [prefs, setPrefs] = useState<UserPreferences>({
    target_job_titles: [],
    target_locations: [],
    remote_preference: 'any',
    experience_level: 'mid',
    min_salary: undefined,
    max_salary: undefined,
  })
  const [jobTitlesInput, setJobTitlesInput] = useState('')
  const [locationsInput, setLocationsInput] = useState('')

  const loadProfile = useCallback(async () => {
    try {
      const profile = await getProfile()
      setUser(profile)
      setPrefs({
        target_job_titles: profile.target_job_titles || [],
        target_locations: profile.target_locations || [],
        remote_preference: profile.remote_preference || 'any',
        experience_level: profile.experience_level || 'mid',
        min_salary: profile.min_salary || undefined,
        max_salary: profile.max_salary || undefined,
      })
      setJobTitlesInput((profile.target_job_titles || []).join(', '))
      setLocationsInput((profile.target_locations || []).join(', '))
    } catch (e) {
      // No user yet
    }
  }, [setUser])

  useEffect(() => {
    loadProfile()
  }, [loadProfile])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const profile = await uploadResume(file)
      setUser(profile)
      setPrefs({
        target_job_titles: profile.target_job_titles || [],
        target_locations: profile.target_locations || [],
        remote_preference: profile.remote_preference || 'any',
        experience_level: profile.experience_level || 'mid',
      })
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Upload failed')
    }
    setUploading(false)
  }

  const handleSavePrefs = async () => {
    setSaving(true)
    try {
      const titles = jobTitlesInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const locations = locationsInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)

      await updatePreferences({
        ...prefs,
        target_job_titles: titles,
        target_locations: locations,
      })
      await loadProfile()
    } catch (err: any) {
      alert('Failed to save preferences')
    }
    setSaving(false)
  }

  const handleStartSearch = async () => {
    try {
      setIsSearching(true)
      await searchJobs()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Search failed')
      setIsSearching(false)
    }
  }

  const handleStartBrowser = async () => {
    try {
      await startBrowser()
      const status = await getBrowserStatus()
      setBrowserStatus(status)
    } catch (err: any) {
      alert('Failed to start browser')
    }
  }

  const handleLogin = async (platform: string) => {
    try {
      await openLogin(platform)
    } catch (err: any) {
      alert(`Failed to open ${platform} login`)
    }
  }

  const cardStyle: React.CSSProperties = {
    background: '#fff',
    borderRadius: 12,
    padding: 24,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    marginBottom: 20,
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    color: '#555',
    marginBottom: 6,
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ddd',
    borderRadius: 8,
    fontSize: 14,
    outline: 'none',
  }

  const buttonStyle: React.CSSProperties = {
    padding: '10px 20px',
    background: '#1a1a2e',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Dashboard</h1>

      {/* Resume Upload */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Upload size={20} />
          <h2 style={{ fontSize: 18, fontWeight: 600 }}>Resume</h2>
        </div>

        {user?.parsed_resume_json ? (
          <div>
            <div
              style={{
                background: '#e8f5e9',
                border: '1px solid #a5d6a7',
                borderRadius: 8,
                padding: 12,
                marginBottom: 12,
                fontSize: 14,
              }}
            >
              Resume uploaded: <strong>{user.full_name}</strong> — {user.email}
              {user.parsed_resume_json?.skills && (
                <div style={{ marginTop: 8, color: '#666' }}>
                  Skills: {(user.parsed_resume_json.skills as string[]).slice(0, 10).join(', ')}
                  {(user.parsed_resume_json.skills as string[]).length > 10 && '...'}
                </div>
              )}
            </div>
            <label style={{ ...buttonStyle, background: '#666', display: 'inline-block' }}>
              Replace Resume
              <input
                type="file"
                accept=".docx"
                onChange={handleUpload}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        ) : (
          <div>
            <p style={{ color: '#666', marginBottom: 12 }}>
              Upload your resume (DOCX) to get started. AI will parse it automatically.
            </p>
            <label
              style={{
                ...buttonStyle,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                opacity: uploading ? 0.6 : 1,
              }}
            >
              <Upload size={16} />
              {uploading ? 'Parsing...' : 'Upload DOCX Resume'}
              <input
                type="file"
                accept=".docx"
                onChange={handleUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        )}
      </div>

      {/* Preferences */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Settings size={20} />
          <h2 style={{ fontSize: 18, fontWeight: 600 }}>Search Preferences</h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label style={labelStyle}>Job Titles (comma separated)</label>
            <input
              style={inputStyle}
              value={jobTitlesInput}
              onChange={(e) => setJobTitlesInput(e.target.value)}
              placeholder="Software Engineer, Full Stack Developer"
            />
          </div>
          <div>
            <label style={labelStyle}>Locations (comma separated)</label>
            <input
              style={inputStyle}
              value={locationsInput}
              onChange={(e) => setLocationsInput(e.target.value)}
              placeholder="Toronto, Remote"
            />
          </div>
          <div>
            <label style={labelStyle}>Remote Preference</label>
            <select
              style={inputStyle}
              value={prefs.remote_preference}
              onChange={(e) => setPrefs({ ...prefs, remote_preference: e.target.value })}
            >
              <option value="any">Any</option>
              <option value="remote">Remote Only</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>Experience Level</label>
            <select
              style={inputStyle}
              value={prefs.experience_level}
              onChange={(e) => setPrefs({ ...prefs, experience_level: e.target.value })}
            >
              <option value="entry">Entry Level</option>
              <option value="mid">Mid Level</option>
              <option value="senior">Senior</option>
              <option value="executive">Executive</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>Min Salary</label>
            <input
              style={inputStyle}
              type="number"
              value={prefs.min_salary || ''}
              onChange={(e) =>
                setPrefs({ ...prefs, min_salary: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="50000"
            />
          </div>
          <div>
            <label style={labelStyle}>Max Salary</label>
            <input
              style={inputStyle}
              type="number"
              value={prefs.max_salary || ''}
              onChange={(e) =>
                setPrefs({ ...prefs, max_salary: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="150000"
            />
          </div>
        </div>

        <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
          <button onClick={handleSavePrefs} disabled={saving} style={buttonStyle}>
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
          <button
            onClick={handleStartSearch}
            disabled={!user?.parsed_resume_json}
            style={{
              ...buttonStyle,
              background: user?.parsed_resume_json ? '#4CAF50' : '#ccc',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Search size={16} /> Start Job Search
            </span>
          </button>
        </div>
      </div>

      {/* Browser Control */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Monitor size={20} />
          <h2 style={{ fontSize: 18, fontWeight: 600 }}>Browser Control</h2>
        </div>
        <p style={{ color: '#666', marginBottom: 12, fontSize: 14 }}>
          Start the browser and log into LinkedIn/Indeed. Your login sessions persist between runs.
        </p>
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={handleStartBrowser} style={buttonStyle}>
            Start Browser
          </button>
          <button
            onClick={() => handleLogin('linkedin')}
            style={{ ...buttonStyle, background: '#0077B5' }}
          >
            Login to LinkedIn
          </button>
          <button
            onClick={() => handleLogin('indeed')}
            style={{ ...buttonStyle, background: '#2164f3' }}
          >
            Login to Indeed
          </button>
        </div>
        {browserStatus.initialized && (
          <div
            style={{
              marginTop: 12,
              fontSize: 13,
              color: '#666',
              display: 'flex',
              gap: 16,
            }}
          >
            <span>
              LinkedIn:{' '}
              <strong style={{ color: browserStatus.linkedin_logged_in ? '#4CAF50' : '#f44336' }}>
                {browserStatus.linkedin_logged_in ? 'Logged in' : 'Not logged in'}
              </strong>
            </span>
            <span>
              Indeed:{' '}
              <strong style={{ color: browserStatus.indeed_logged_in ? '#4CAF50' : '#f44336' }}>
                {browserStatus.indeed_logged_in ? 'Logged in' : 'Not logged in'}
              </strong>
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
