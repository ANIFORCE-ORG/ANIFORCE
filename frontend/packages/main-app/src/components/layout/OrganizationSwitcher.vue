<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { organizationApi, type OrganizationResponse } from '@/api/organization'

const TEAM_STORAGE_KEY = 'animagus_current_team'
const loading = ref(false)
const teams = ref<OrganizationResponse[]>([])
const selectedTeamId = ref(localStorage.getItem(TEAM_STORAGE_KEY) || '')

const currentTeam = computed(() => {
  return teams.value.find((team) => team.id === selectedTeamId.value) || teams.value[0] || null
})

const demoTeams: OrganizationResponse[] = [
  {
    id: 'org-aniforce-growth',
    name: 'ANIFORCE Growth',
    org_code: 'ANIFORCE',
    description: 'Demo team',
    owner_id: 'demo-user',
    status: 'active',
    member_count: 4,
    role: 'admin',
    created_at: '2026-05-01T09:00:00Z',
  },
]

const selectTeam = (teamId: string) => {
  selectedTeamId.value = teamId
  localStorage.setItem(TEAM_STORAGE_KEY, teamId)
}

const loadOrganizations = async () => {
  loading.value = true
  try {
    const data = await organizationApi.getMyOrganizations()
    if (data.length > 0) {
      teams.value = data
      if (!data.some((team) => team.id === selectedTeamId.value)) {
        selectTeam(data[0].id)
      }
    } else {
      teams.value = demoTeams
      selectTeam(demoTeams[0].id)
    }
  } catch {
    teams.value = demoTeams
    selectTeam(demoTeams[0].id)
  } finally {
    loading.value = false
  }
}

const handleSelect = async (event: Event) => {
  selectTeam((event.target as HTMLSelectElement).value)
}

onMounted(() => {
  loadOrganizations()
})
</script>

<template>
  <div class="rounded-md border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
    <div class="mb-2 flex items-center justify-between gap-3">
      <div class="min-w-0">
        <div class="text-xs font-medium text-slate-500 dark:text-slate-400">当前团队</div>
        <div class="truncate text-sm font-semibold text-slate-900 dark:text-white">
          {{ currentTeam?.name || '未选择团队' }}
        </div>
      </div>
      <span class="material-symbols-outlined text-primary text-lg">groups</span>
    </div>
    <select
      class="w-full rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm text-slate-700 outline-none transition-colors focus:border-primary focus:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
      :value="selectedTeamId"
      :disabled="loading"
      @change="handleSelect"
    >
      <option
        v-for="team in teams"
        :key="team.id"
        :value="team.id"
      >
        {{ team.name }}
      </option>
    </select>
  </div>
</template>
