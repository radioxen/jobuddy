import { create } from 'zustand'
import type { UserProfile, JobListing, Application } from '../types'

interface AppState {
  // User
  user: UserProfile | null
  setUser: (user: UserProfile | null) => void

  // Jobs
  jobs: JobListing[]
  setJobs: (jobs: JobListing[]) => void
  totalJobs: number
  setTotalJobs: (total: number) => void

  // Applications
  applications: Application[]
  setApplications: (apps: Application[]) => void

  // UI State
  activeTab: string
  setActiveTab: (tab: string) => void
  isSearching: boolean
  setIsSearching: (v: boolean) => void
  notifications: { id: string; message: string; type: string }[]
  addNotification: (message: string, type?: string) => void
  removeNotification: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),

  jobs: [],
  setJobs: (jobs) => set({ jobs }),
  totalJobs: 0,
  setTotalJobs: (totalJobs) => set({ totalJobs }),

  applications: [],
  setApplications: (applications) => set({ applications }),

  activeTab: 'dashboard',
  setActiveTab: (activeTab) => set({ activeTab }),
  isSearching: false,
  setIsSearching: (isSearching) => set({ isSearching }),

  notifications: [],
  addNotification: (message, type = 'info') =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { id: Date.now().toString(), message, type },
      ],
    })),
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}))
