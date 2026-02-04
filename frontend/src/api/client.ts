import axios from 'axios'
import type { UserProfile, UserPreferences, JobListing, Application } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
})

// Users
export const uploadResume = async (file: File): Promise<UserProfile> => {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/users/upload-resume', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const getProfile = async (): Promise<UserProfile> => {
  const { data } = await api.get('/users/profile')
  return data
}

export const updatePreferences = async (prefs: UserPreferences): Promise<UserPreferences> => {
  const { data } = await api.put('/users/preferences', prefs)
  return data
}

export const getPreferences = async (): Promise<UserPreferences> => {
  const { data } = await api.get('/users/preferences')
  return data
}

// Jobs
export const searchJobs = async (params?: {
  job_titles?: string[]
  locations?: string[]
  platforms?: string[]
  max_results?: number
}) => {
  const { data } = await api.post('/jobs/search', params || {})
  return data
}

export const getJobs = async (params?: {
  status?: string
  min_score?: number
  source?: string
  page?: number
  per_page?: number
}): Promise<{ jobs: JobListing[]; total: number; page: number; per_page: number }> => {
  const { data } = await api.get('/jobs', { params })
  return data
}

export const getJob = async (id: number): Promise<JobListing> => {
  const { data } = await api.get(`/jobs/${id}`)
  return data
}

export const approveJob = async (id: number) => {
  const { data } = await api.post(`/jobs/${id}/approve`)
  return data
}

export const rejectJob = async (id: number) => {
  const { data } = await api.post(`/jobs/${id}/reject`)
  return data
}

export const approveJobsBatch = async (jobIds: number[]) => {
  const { data } = await api.post('/jobs/approve-batch', { job_ids: jobIds })
  return data
}

// Applications
export const getApplications = async (status?: string): Promise<{ applications: Application[]; total: number }> => {
  const { data } = await api.get('/applications', { params: status ? { status } : {} })
  return data
}

export const prepareDocuments = async (appId: number) => {
  const { data } = await api.post(`/applications/${appId}/prepare`)
  return data
}

export const fillForm = async (appId: number) => {
  const { data } = await api.post(`/applications/${appId}/fill-form`)
  return data
}

export const prepareAllApproved = async () => {
  const { data } = await api.post('/applications/prepare-all')
  return data
}

export const downloadResume = (appId: number) =>
  `/api/v1/applications/${appId}/resume/download`

export const downloadCoverLetter = (appId: number) =>
  `/api/v1/applications/${appId}/cover-letter/download`

// Browser
export const startBrowser = async () => {
  const { data } = await api.post('/browser/start')
  return data
}

export const getBrowserStatus = async () => {
  const { data } = await api.get('/browser/status')
  return data
}

export const openLogin = async (platform: string) => {
  const { data } = await api.post(`/browser/login/${platform}`)
  return data
}
