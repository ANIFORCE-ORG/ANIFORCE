import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Campaign {
  id: string
  name: string
  project_id: string
  platform: string
  status: string
  budget: number
  spend: number
  installs: number
  target_cpa?: number
  roi: number
  pipeline_step?: string
  created_at?: string
}

export const useCampaignsStore = defineStore('campaigns', () => {
  const campaigns = ref<Campaign[]>([])
  const loading = ref(false)

  const fetchCampaigns = async () => {
    loading.value = true
    try {
      // Mock data for demo mode
      campaigns.value = [
        {
          id: 'camp_001',
          name: 'Candy Blast - US iOS',
          project_id: 'proj_001',
          platform: 'Meta',
          status: 'running',
          budget: 5000,
          spend: 3200,
          installs: 1280,
          target_cpa: 2.5,
          roi: 2.8,
          pipeline_step: 'scaling',
          created_at: '2024-01-20'
        },
        {
          id: 'camp_002',
          name: 'Candy Blast - UK Android',
          project_id: 'proj_001',
          platform: 'Google',
          status: 'running',
          budget: 3000,
          spend: 2100,
          installs: 840,
          target_cpa: 2.8,
          roi: 2.3,
          pipeline_step: 'testing',
          created_at: '2024-01-22'
        },
        {
          id: 'camp_003',
          name: 'DramaBox - US TikTok',
          project_id: 'proj_002',
          platform: 'TikTok',
          status: 'running',
          budget: 8000,
          spend: 6500,
          installs: 2600,
          target_cpa: 3.0,
          roi: 3.2,
          pipeline_step: 'scaling',
          created_at: '2024-02-05'
        },
        {
          id: 'camp_004',
          name: 'Racing Master - EU Meta',
          project_id: 'proj_003',
          platform: 'Meta',
          status: 'running',
          budget: 4000,
          spend: 2800,
          installs: 933,
          target_cpa: 3.5,
          roi: 1.9,
          pipeline_step: 'testing',
          created_at: '2024-03-15'
        }
      ]
    } finally {
      loading.value = false
    }
  }

  return {
    campaigns,
    loading,
    fetchCampaigns
  }
})
