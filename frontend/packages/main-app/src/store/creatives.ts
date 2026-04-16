import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Creative {
  id: string
  name: string
  type: string
  status: string
  thumb?: string
  ctr?: number
  cvr?: number
  spend?: number
  roi?: number
  created_at?: string
}

export const useCreativesStore = defineStore('creatives', () => {
  const creatives = ref<Creative[]>([])
  const loading = ref(false)

  const fetchCreatives = async () => {
    loading.value = true
    try {
      // Mock data for demo mode
      creatives.value = [
        {
          id: 'creative_001',
          name: 'Candy Blast - UGC Fail Moment',
          type: 'video',
          status: 'running',
          thumb: 'https://via.placeholder.com/150',
          ctr: 0.082,
          cvr: 0.045,
          spend: 1200,
          roi: 3.5,
          created_at: '2024-01-25'
        },
        {
          id: 'creative_002',
          name: 'Candy Blast - Gameplay Demo',
          type: 'video',
          status: 'running',
          thumb: 'https://via.placeholder.com/150',
          ctr: 0.065,
          cvr: 0.038,
          spend: 980,
          roi: 2.8,
          created_at: '2024-01-26'
        },
        {
          id: 'creative_003',
          name: 'DramaBox - 霸总剧情',
          type: 'video',
          status: 'running',
          thumb: 'https://via.placeholder.com/150',
          ctr: 0.071,
          cvr: 0.042,
          spend: 2100,
          roi: 3.2,
          created_at: '2024-02-08'
        },
        {
          id: 'creative_004',
          name: 'Racing Master - Car Chase',
          type: 'video',
          status: 'running',
          thumb: 'https://via.placeholder.com/150',
          ctr: 0.058,
          cvr: 0.032,
          spend: 850,
          roi: 2.1,
          created_at: '2024-03-18'
        },
        {
          id: 'creative_005',
          name: 'Candy Blast - Tutorial',
          type: 'video',
          status: 'running',
          thumb: 'https://via.placeholder.com/150',
          ctr: 0.048,
          cvr: 0.028,
          spend: 650,
          roi: 1.8,
          created_at: '2024-01-28'
        }
      ]
    } finally {
      loading.value = false
    }
  }

  return {
    creatives,
    loading,
    fetchCreatives
  }
})
