import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Project {
  id: string
  name: string
  product_type: string
  region: string[]
  budget: number
  spend?: number
  status: string
  created_at?: string
}

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const loading = ref(false)

  const fetchProjects = async () => {
    loading.value = true
    try {
      // Mock data for demo mode
      projects.value = [
        {
          id: 'proj_001',
          name: 'Candy Blast',
          product_type: 'Puzzle',
          region: ['US', 'UK'],
          budget: 50000,
          spend: 32000,
          status: 'active',
          created_at: '2024-01-15'
        },
        {
          id: 'proj_002',
          name: 'DramaBox',
          product_type: 'Entertainment',
          region: ['US', 'CA'],
          budget: 80000,
          spend: 65000,
          status: 'active',
          created_at: '2024-02-01'
        },
        {
          id: 'proj_003',
          name: 'Racing Master',
          product_type: 'Racing',
          region: ['US', 'EU'],
          budget: 60000,
          spend: 28000,
          status: 'active',
          created_at: '2024-03-10'
        }
      ]
    } finally {
      loading.value = false
    }
  }

  return {
    projects,
    loading,
    fetchProjects
  }
})
