<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'
import {
  createOrganization,
  getOrganizationMembers,
  getOrganizations,
  inviteOrganizationMember,
  type Organization,
  type OrganizationMember,
  type OrganizationRole,
  type OrganizationType,
} from '@/api/organizations'
import { useOrganizationContext } from '@/composables/useOrganizationContext'

const router = useRouter()
const {
  organizations,
  currentOrganization,
  selectedOrganizationId,
  useDemoOrganizations,
  selectOrganization,
  addLocalOrganization,
  getDemoMembers,
} = useOrganizationContext()

const loading = ref(false)
const membersLoading = ref(false)
const members = ref<OrganizationMember[]>([])
const showCreateForm = ref(false)
const showInviteForm = ref(false)
const apiNotice = ref('')

const organizationForm = ref<{
  name: string
  type: OrganizationType
}>({
  name: '',
  type: 'advertiser',
})

const inviteForm = ref<{
  email: string
  role: OrganizationRole
}>({
  email: '',
  role: 'operator',
})

const currentMembers = computed(() => members.value)

const switchPanel = (item: { path?: string }) => {
  if (item.path) {
    router.push(item.path)
  }
}

const roleLabel = (role: OrganizationRole) => {
  const labels: Record<OrganizationRole, string> = {
    owner: 'Owner',
    manager: 'Manager',
    operator: 'Operator',
  }
  return labels[role]
}

const typeLabel = (type: OrganizationType) => {
  return type === 'agency' ? '代理商组织' : '广告主组织'
}

const statusLabel = (status: OrganizationMember['status']) => {
  const labels: Record<OrganizationMember['status'], string> = {
    active: '已加入',
    invited: '已邀请',
    requested: '待审核',
    disabled: '已停用',
  }
  return labels[status]
}

const loadMembers = async (organizationId: string) => {
  membersLoading.value = true
  try {
    members.value = await getOrganizationMembers(organizationId)
  } catch {
    members.value = getDemoMembers(organizationId)
    apiNotice.value = '组织接口未就绪，当前展示前端 Demo 数据。'
  } finally {
    membersLoading.value = false
  }
}

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
      apiNotice.value = '组织列表为空，当前展示前端 Demo 数据。'
    }
  } catch {
    useDemoOrganizations()
    apiNotice.value = '组织接口未就绪，当前展示前端 Demo 数据。'
  } finally {
    loading.value = false
  }

  if (currentOrganization.value) {
    await loadMembers(currentOrganization.value.id)
  }
}

const handleSelectOrganization = async (organizationId: string) => {
  selectOrganization(organizationId)
  await loadMembers(organizationId)
}

const handleCreateOrganization = async () => {
  const name = organizationForm.value.name.trim()
  if (!name) return

  try {
    const organization = await createOrganization({
      name,
      type: organizationForm.value.type,
    })
    addLocalOrganization(organization)
    apiNotice.value = ''
  } catch {
    const localOrganization: Organization = {
      id: `org-local-${Date.now()}`,
      name,
      type: organizationForm.value.type,
      role: 'owner',
      status: 'active',
      member_count: 1,
      platform_account_count: 0,
      project_count: 0,
      created_at: new Date().toISOString(),
    }
    addLocalOrganization(localOrganization)
    members.value = [
      {
        id: `member-local-${Date.now()}`,
        user_id: 'admin-001',
        name: 'Admin',
        email: 'test@animagus.com',
        role: 'owner',
        status: 'active',
        joined_at: new Date().toISOString(),
      },
    ]
    apiNotice.value = '组织接口未就绪，新组织仅保存为本地 Demo 数据。'
  }

  organizationForm.value = { name: '', type: 'advertiser' }
  showCreateForm.value = false
}

const handleInviteMember = async () => {
  const email = inviteForm.value.email.trim()
  if (!email || !currentOrganization.value) return

  try {
    const member = await inviteOrganizationMember(currentOrganization.value.id, {
      email,
      role: inviteForm.value.role,
    })
    members.value = [member, ...members.value]
    apiNotice.value = ''
  } catch {
    members.value = [
      {
        id: `member-invited-${Date.now()}`,
        user_id: `pending-${Date.now()}`,
        name: email.split('@')[0],
        email,
        role: inviteForm.value.role,
        status: 'invited',
        joined_at: new Date().toISOString(),
      },
      ...members.value,
    ]
    apiNotice.value = '邀请接口未就绪，邀请记录仅保存为本地 Demo 数据。'
  }

  inviteForm.value = { email: '', role: 'operator' }
  showInviteForm.value = false
}

onMounted(() => {
  loadOrganizations()
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="[]"
      active-panel="settings"
      @switch-panel="switchPanel"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
        <div class="flex items-center gap-3">
          <button
            class="rounded-md p-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-700"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">组织与权限</h1>
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
              管理组织、成员角色和后续广告账户的数据隔离边界
            </p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div class="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <section class="space-y-4">
            <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
              <div class="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 class="text-base font-semibold text-slate-900 dark:text-white">组织列表</h2>
                  <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">组织是项目、素材和广告账户的隔离边界</p>
                </div>
                <button
                  class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90 whitespace-nowrap"
                  @click="showCreateForm = true"
                >
                  新建组织
                </button>
              </div>

              <div v-if="apiNotice" class="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                {{ apiNotice }}
              </div>

              <div v-if="loading" class="py-8 text-center text-sm text-slate-500">加载组织中...</div>
              <div v-else class="space-y-2">
                <button
                  v-for="organization in organizations"
                  :key="organization.id"
                  class="w-full rounded-md border p-3 text-left transition-colors"
                  :class="selectedOrganizationId === organization.id
                    ? 'border-primary bg-primary/5'
                    : 'border-slate-200 hover:border-primary/50 dark:border-slate-700'"
                  @click="handleSelectOrganization(organization.id)"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="min-w-0">
                      <div class="truncate text-sm font-semibold text-slate-900 dark:text-white">{{ organization.name }}</div>
                      <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ typeLabel(organization.type) }}</div>
                    </div>
                    <span class="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                      {{ roleLabel(organization.role) }}
                    </span>
                  </div>
                  <div class="mt-3 grid grid-cols-3 gap-2 text-center text-xs text-slate-500 dark:text-slate-400">
                    <div class="rounded bg-slate-50 py-2 dark:bg-slate-900">
                      <div class="font-semibold text-slate-900 dark:text-white">{{ organization.member_count }}</div>
                      成员
                    </div>
                    <div class="rounded bg-slate-50 py-2 dark:bg-slate-900">
                      <div class="font-semibold text-slate-900 dark:text-white">{{ organization.platform_account_count }}</div>
                      账户
                    </div>
                    <div class="rounded bg-slate-50 py-2 dark:bg-slate-900">
                      <div class="font-semibold text-slate-900 dark:text-white">{{ organization.project_count }}</div>
                      项目
                    </div>
                  </div>
                </button>
              </div>
            </div>

            <div
              v-if="showCreateForm"
              class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800"
            >
              <h3 class="text-sm font-semibold text-slate-900 dark:text-white">新建组织</h3>
              <div class="mt-4 space-y-3">
                <label class="block">
                  <span class="text-sm text-slate-600 dark:text-slate-400">组织名称</span>
                  <input
                    v-model="organizationForm.name"
                    class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-primary dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                    placeholder="例如 ANIFORCE Growth"
                  />
                </label>
                <label class="block">
                  <span class="text-sm text-slate-600 dark:text-slate-400">组织类型</span>
                  <select
                    v-model="organizationForm.type"
                    class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-primary dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                  >
                    <option value="advertiser">广告主组织</option>
                    <option value="agency">代理商组织</option>
                  </select>
                </label>
                <div class="flex justify-end gap-2">
                  <button
                    class="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                    @click="showCreateForm = false"
                  >
                    取消
                  </button>
                  <button
                    class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary/90"
                    @click="handleCreateOrganization"
                  >
                    创建
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section class="space-y-4">
            <div class="rounded-md border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
              <div class="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 class="text-base font-semibold text-slate-900 dark:text-white">
                    {{ currentOrganization?.name || '当前组织' }}
                  </h2>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    {{ currentOrganization ? typeLabel(currentOrganization.type) : '选择组织后查看成员和权限' }}
                  </p>
                </div>
                <button
                  class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90 whitespace-nowrap"
                  @click="showInviteForm = true"
                >
                  邀请成员
                </button>
              </div>

              <div class="mt-5 grid gap-3 md:grid-cols-3">
                <div class="rounded-md bg-slate-50 p-4 dark:bg-slate-900">
                  <div class="text-xs text-slate-500 dark:text-slate-400">成员数</div>
                  <div class="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
                    {{ currentOrganization?.member_count || currentMembers.length }}
                  </div>
                </div>
                <div class="rounded-md bg-slate-50 p-4 dark:bg-slate-900">
                  <div class="text-xs text-slate-500 dark:text-slate-400">广告账户</div>
                  <div class="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
                    {{ currentOrganization?.platform_account_count || 0 }}
                  </div>
                </div>
                <div class="rounded-md bg-slate-50 p-4 dark:bg-slate-900">
                  <div class="text-xs text-slate-500 dark:text-slate-400">业务项目</div>
                  <div class="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
                    {{ currentOrganization?.project_count || 0 }}
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="showInviteForm"
              class="rounded-md border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800"
            >
              <h3 class="text-sm font-semibold text-slate-900 dark:text-white">邀请成员</h3>
              <div class="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto]">
                <input
                  v-model="inviteForm.email"
                  class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-primary dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                  placeholder="member@company.com"
                />
                <select
                  v-model="inviteForm.role"
                  class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-primary dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                >
                  <option value="manager">Manager</option>
                  <option value="operator">Operator</option>
                </select>
                <div class="flex gap-2">
                  <button
                    class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary/90 whitespace-nowrap"
                    @click="handleInviteMember"
                  >
                    发送邀请
                  </button>
                  <button
                    class="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                    @click="showInviteForm = false"
                  >
                    取消
                  </button>
                </div>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
              <div class="border-b border-slate-200 px-5 py-4 dark:border-slate-700">
                <h3 class="text-sm font-semibold text-slate-900 dark:text-white">成员与权限</h3>
              </div>
              <div v-if="membersLoading" class="py-12 text-center text-sm text-slate-500">加载成员中...</div>
              <div v-else class="divide-y divide-slate-200 dark:divide-slate-700">
                <div
                  v-for="member in currentMembers"
                  :key="member.id"
                  class="grid gap-3 px-5 py-4 md:grid-cols-[minmax(0,1fr)_120px_110px] md:items-center"
                >
                  <div class="min-w-0">
                    <div class="truncate text-sm font-semibold text-slate-900 dark:text-white">{{ member.name }}</div>
                    <div class="truncate text-xs text-slate-500 dark:text-slate-400">{{ member.email }}</div>
                  </div>
                  <span class="w-fit rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                    {{ roleLabel(member.role) }}
                  </span>
                  <span class="w-fit rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {{ statusLabel(member.status) }}
                  </span>
                </div>
                <div v-if="currentMembers.length === 0" class="py-12 text-center text-sm text-slate-500">
                  暂无成员数据
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>
