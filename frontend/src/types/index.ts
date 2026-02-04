export interface UserProfile {
  id: number
  full_name: string
  email: string
  phone: string | null
  linkedin_url: string | null
  original_resume_path: string | null
  parsed_resume_json: Record<string, any> | null
  target_job_titles: string[] | null
  target_locations: string[] | null
  remote_preference: string
  min_salary: number | null
  max_salary: number | null
  experience_level: string
  industries: string[] | null
  created_at: string
  updated_at: string
}

export interface UserPreferences {
  target_job_titles?: string[]
  target_locations?: string[]
  remote_preference?: string
  min_salary?: number
  max_salary?: number
  experience_level?: string
  industries?: string[]
}

export interface JobListing {
  id: number
  source: string
  source_url: string
  source_job_id: string | null
  title: string
  company: string
  location: string
  description: string
  salary_info: string | null
  job_type: string | null
  posted_date: string | null
  is_easy_apply: boolean
  fit_score: number | null
  fit_reasoning: string | null
  status: string
  created_at: string
}

export interface Application {
  id: number
  job_id: number
  user_id: number
  tailored_resume_path: string | null
  cover_letter_path: string | null
  cover_letter_text: string | null
  status: string
  form_data_json: Record<string, any> | null
  error_message: string | null
  submitted_at: string | null
  created_at: string
  updated_at: string
  job?: JobListing
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  message_type?: string
  timestamp?: string
}

export interface WSMessage {
  type: string
  payload: Record<string, any>
  timestamp: string
}
