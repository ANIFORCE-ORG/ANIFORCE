<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getOrganizations, setCurrentOrganization } from '@/api/organizations'
import { useOrganizationContext } from '@/composables/useOrganizationContext'

const {
  organizations,
  currentOrganization,
  selectedOrganizationId,
  useDemoOrganizations,
  selectOrganization,
} = useOrganizationContext()

const loading = ref(false)

const loadOrganizations = async () => {
  loading.value = true
  try {
    const data = await getOrganizations()
    if (data.length > 0) {
      organizations.value = data
      if (!data.some((organization) => organization.id === selectedOrganizationId.value)) {
        selectOrganization(data[0].id)
      }
    } else {
      useDemoOrganizations()
    }
  } catch {
    useDemoOrganizations()
  } finally {
    loading.value = false
  }
}

const handleSelect = async (event: Event) => {
  const organizationId = (event.target as HTMLSelectElement).value
  selectOrganization(organizationId)
  try {
    await setCurrentOrganization(organizationId)
  } catch {
    // Backend organization context is not available in local demo yet.
  }
}

onMounted(() => {
  loadOrganizations()
})
</script>

<template>
  <div class="rounded-md border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
    <div class="mb-2 flex items-center justify-between gap-3">
      <div class="min-w-0">
        <div class="text-xs font-medium text-slate-500 dark:text-slate-400">当前组织</div>
        <div class="truncate text-sm font-semibold text-slate-900 dark:text-white">
          {{ currentOrganization?.name || '未选择组织' }}
        </div>
      </div>
      <span class="material-symbols-outlined text-primary text-lg">corporate_fare</span>
    </div>
    <select
      class="w-full rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm text-slate-700 outline-none transition-colors focus:border-primary focus:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
      :value="selectedOrganizationId"
      :disabled="loading"
      @change="handleSelect"
    >
      <option
        v-for="organization in organizations"
        :key="organization.id"
        :value="organization.id"
      >
        {{ organization.name }}
      </option>
    </select>
  </div>
</template>
