<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'
import { userApi } from '@/api/user'
import { organizationApi, type OrganizationResponse } from '@/api/organization'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import OrganizationDetail from '@/components/settings/OrganizationDetail.vue'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const { success, error } = useToast()

const activePanel = ref('settings')
const activeSession = ref('sess_g001')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false }
])

const userEmail = ref(auth.user?.email || 'test@animagus.com')
const userName = ref(auth.user?.name || '用户')
const isEditingName = ref(false)
const newName = ref('')
const isChangingPassword = ref(false)
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordError = ref('')

// 密码显示状态
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

const currentPlan = ref({
  name: 'Seed',
  icon: '🌱',
  color: 'text-orange-600',
  bgColor: 'bg-orange-50 dark:bg-orange-900/30'
})

const usage = ref({
  monthlyUsed: 2.40,
  monthlyLimit: 100,
  aiCalls: 156,
  aiCallsLimit: 10000,
  materialsGenerated: 23,
  materialsLimit: 500
})

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleEditName = () => {
  newName.value = userName.value
  isEditingName.value = true
}

const handleSaveName = async () => {
  if (!newName.value.trim()) {
    error('用户名不能为空')
    return
  }
  
  try {
    const updatedUser = await userApi.updateName({ name: newName.value.trim() })
    userName.value = updatedUser.name
    auth.user = updatedUser
    isEditingName.value = false
    success('用户名更新成功')
  } catch (err: any) {
    console.error('更新用户名失败:', err)
    error(err.response?.data?.detail || '更新用户名失败，请稍后重试')
  }
}

const handleCancelEditName = () => {
  isEditingName.value = false
  newName.value = ''
}

const handleChangePassword = () => {
  isChangingPassword.value = true
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
  passwordError.value = ''
}

const handleSavePassword = async () => {
  passwordError.value = ''
  
  if (!passwordForm.value.currentPassword || !passwordForm.value.newPassword || !passwordForm.value.confirmPassword) {
    passwordError.value = '请填写所有密码字段'
    return
  }
  
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = '新密码与确认密码不一致'
    return
  }
  
  if (passwordForm.value.newPassword.length < 6) {
    passwordError.value = '新密码长度至少为 6 个字符'
    return
  }
  
  try {
    await userApi.updatePassword({
      current_password: passwordForm.value.currentPassword,
      new_password: passwordForm.value.newPassword
    })
    
    isChangingPassword.value = false
    passwordForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
    success('密码修改成功')
  } catch (err: any) {
    console.error('更新密码失败:', err)
    passwordError.value = err.response?.data?.detail || '密码修改失败，请检查当前密码是否正确'
  }
}

const handleCancelChangePassword = () => {
  isChangingPassword.value = false
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
  passwordError.value = ''
}

const handleUpgradePlan = () => {
  console.log('升级套餐')
}

// 团队相关
const myOrganizations = ref<OrganizationResponse[]>([])

// 创建团队弹窗
const showCreateOrgDialog = ref(false)
const createOrgForm = ref({
  name: '',
  orgId: '',
  description: ''
})
const createOrgError = ref('')

// 加入团队弹窗
const showJoinOrgDialog = ref(false)
const joinOrgForm = ref({
  orgId: '',
  inviteCode: ''
})
const joinOrgError = ref('')

// 确认对话框
const showConfirmDialog = ref(false)
const confirmDialogConfig = ref({
  title: '',
  message: '',
  confirmText: '确定',
  confirmButtonClass: 'bg-red-500 hover:bg-red-600',
  onConfirm: () => {}
})

// 团队详情弹窗
const showOrgDetailDialog = ref(false)
const selectedOrganization = ref<OrganizationResponse | null>(null)

const handleCreateOrganization = () => {
  console.log('创建团队按钮被点击')
  showCreateOrgDialog.value = true
  createOrgForm.value = {
    name: '',
    orgId: '',
    description: ''
  }
  createOrgError.value = ''
}

const handleCancelCreateOrg = () => {
  showCreateOrgDialog.value = false
  createOrgForm.value = {
    name: '',
    orgId: '',
    description: ''
  }
  createOrgError.value = ''
}

const handleSubmitCreateOrg = async () => {
  createOrgError.value = ''
  
  // 验证表单
  if (!createOrgForm.value.name.trim()) {
    createOrgError.value = '请输入团队名称'
    return
  }
  if (!createOrgForm.value.orgId.trim()) {
    createOrgError.value = '请输入团队 ID'
    return
  }
  
  try {
    const newOrg = await organizationApi.create({
      name: createOrgForm.value.name,
      org_code: createOrgForm.value.orgId,
      description: createOrgForm.value.description || undefined
    })
    
    myOrganizations.value.push(newOrg)
    showCreateOrgDialog.value = false
    success('团队创建成功')
  } catch (err: any) {
    console.error('创建团队失败:', err)
    createOrgError.value = err.response?.data?.detail || '创建团队失败，请稍后重试'
  }
}

const handleJoinOrganization = () => {
  showJoinOrgDialog.value = true
  joinOrgForm.value = {
    orgId: '',
    inviteCode: ''
  }
  joinOrgError.value = ''
}

const handleCancelJoinOrg = () => {
  showJoinOrgDialog.value = false
  joinOrgForm.value = {
    orgId: '',
    inviteCode: ''
  }
  joinOrgError.value = ''
}

const handleSubmitJoinOrg = async () => {
  joinOrgError.value = ''
  
  // 验证表单
  if (!joinOrgForm.value.orgId.trim()) {
    joinOrgError.value = '请输入团队 ID'
    return
  }
  if (!joinOrgForm.value.inviteCode.trim()) {
    joinOrgError.value = '请输入邀请码'
    return
  }
  
  try {
    const joinedOrg = await organizationApi.join({
      org_code: joinOrgForm.value.orgId,
      invite_code: joinOrgForm.value.inviteCode
    })
    
    myOrganizations.value.push(joinedOrg)
    showJoinOrgDialog.value = false
    success('成功加入团队')
  } catch (err: any) {
    console.error('加入团队失败:', err)
    joinOrgError.value = err.response?.data?.detail || '加入团队失败，请检查团队 ID 和邀请码'
  }
}

const handleViewOrganization = (org: OrganizationResponse) => {
  selectedOrganization.value = org
  showOrgDetailDialog.value = true
}

const handleManageMembers = (orgId: string) => {
  console.log('管理成员:', orgId)
  // TODO: 跳转到团队成员管理页面
}

const handleDisbandOrganization = (orgId: string) => {
  console.log('解散团队:', orgId)
  const org = myOrganizations.value.find(o => o.id === orgId)
  if (!org) return
  
  confirmDialogConfig.value = {
    title: '解散团队',
    message: `确定要解散「${org.name}」吗？此操作不可恢复，所有成员将失去访问权限。`,
    confirmText: '解散团队',
    confirmButtonClass: 'bg-red-500 hover:bg-red-600',
    onConfirm: async () => {
      try {
        await organizationApi.disband(orgId)
        const index = myOrganizations.value.findIndex(o => o.id === orgId)
        if (index !== -1) {
          myOrganizations.value.splice(index, 1)
        }
        success('团队已解散')
      } catch (err: any) {
        console.error('解散团队失败:', err)
        error(err.response?.data?.detail || '解散团队失败')
      }
    }
  }
  showConfirmDialog.value = true
}

const handleLeaveOrganization = (orgId: string) => {
  console.log('离开团队:', orgId)
  const org = myOrganizations.value.find(o => o.id === orgId)
  if (!org) return
  
  confirmDialogConfig.value = {
    title: '离开团队',
    message: `确定要离开「${org.name}」吗？离开后需要重新获取邀请才能加入。`,
    confirmText: '离开团队',
    confirmButtonClass: 'bg-red-500 hover:bg-red-600',
    onConfirm: async () => {
      try {
        await organizationApi.leave(orgId)
        const index = myOrganizations.value.findIndex(o => o.id === orgId)
        if (index !== -1) {
          myOrganizations.value.splice(index, 1)
        }
        success('已离开团队')
      } catch (err: any) {
        console.error('离开团队失败:', err)
        error(err.response?.data?.detail || '离开团队失败')
      }
    }
  }
  showConfirmDialog.value = true
}

const handleConfirmDialogClose = () => {
  showConfirmDialog.value = false
}

const handleConfirmDialogConfirm = () => {
  confirmDialogConfig.value.onConfirm()
  showConfirmDialog.value = false
}

const loadOrganizations = async () => {
  try {
    myOrganizations.value = await organizationApi.getMyOrganizations()
  } catch (err: any) {
    console.error('加载组织列表失败:', err)
    error('加载组织列表失败')
  }
}

const handleCloseOrgDetail = () => {
  showOrgDetailDialog.value = false
  selectedOrganization.value = null
}

const handleRefreshOrganizations = () => {
  loadOrganizations()
}

onMounted(() => {
  console.log('账号配置页面加载')
  loadOrganizations()
})
</script>

<template>
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-[19px] py-[12px]">
        <div class="flex items-center gap-[12px]">
          <button
            class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">arrow_back</span>
          </button>
          <div>
            <h1 class="text-[15px] font-bold text-slate-900 dark:text-white">系统账号设置</h1>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1">管理团队成员、登录身份和基础账号信息</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-[19px]">
        <div class="space-y-[19px]">
          <!-- 登录账户信息 -->
          <section>
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white mb-[12px]">登录账户信息</h3>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-[19px] space-y-[12px]">
              <!-- Email（只读） -->
              <div class="pb-[12px] border-b border-slate-200 dark:border-slate-700">
                <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">邮箱地址</div>
                <div class="text-[13px] font-medium text-slate-900 dark:text-white">{{ userEmail }}</div>
                <!-- <div class="text-xs text-slate-400 dark:text-slate-500 mt-1">邮箱地址不可修改</div>  -->
              </div>

              <!-- 用户名（可编辑） -->
              <div class="flex items-center justify-between pb-[12px] border-b border-slate-200 dark:border-slate-700">
                <div class="flex-1">
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">用户名</div>
                  <div v-if="!isEditingName" class="text-[13px] font-medium text-slate-900 dark:text-white">{{ userName }}</div>
                  <input
                    v-else
                    v-model="newName"
                    type="text"
                    class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
                    placeholder="请输入新用户名"
                  />
                </div>
                <div class="flex items-center gap-[8px] ml-[12px]">
                  <button
                    v-if="!isEditingName"
                    class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    @click="handleEditName"
                  >
                    <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">edit</span>
                  </button>
                  <template v-else>
                    <button
                      class="px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors text-[11px]"
                      @click="handleSaveName"
                    >
                      保存
                    </button>
                    <button
                      class="px-[12px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-[11px]"
                      @click="handleCancelEditName"
                    >
                      取消
                    </button>
                  </template>
                </div>
              </div>

              <!-- 密码 -->
              <div>
                <div class="flex items-center justify-between">
                  <div class="flex-1">
                    <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">密码</div>
                    <div v-if="!isChangingPassword" class="text-[13px] font-medium text-slate-900 dark:text-white">••••••••</div>
                    
                    <!-- 密码修改表单 -->
                    <div v-else class="space-y-[12px] mt-[8px]">
                      <div>
                        <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-1">当前密码</label>
                        <input
                          v-model="passwordForm.currentPassword"
                          type="password"
                          class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
                          placeholder="请输入当前密码"
                        />
                      </div>
                      <div>
                        <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-1">新密码</label>
                        <div class="relative">
                          <input
                            v-model="passwordForm.newPassword"
                            :type="showNewPassword ? 'text' : 'password'"
                            class="w-full px-[12px] py-[8px] pr-[39px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
                            placeholder="请输入新密码（至少6个字符）"
                          />
                          <button
                            type="button"
                            @click="showNewPassword = !showNewPassword"
                            class="absolute right-[8px] top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                          >
                            <span class="material-symbols-outlined text-[17px]">
                              {{ showNewPassword ? 'visibility_off' : 'visibility' }}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div>
                        <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-1">确认新密码</label>
                        <div class="relative">
                          <input
                            v-model="passwordForm.confirmPassword"
                            :type="showConfirmPassword ? 'text' : 'password'"
                            class="w-full px-[12px] py-[8px] pr-[39px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
                            placeholder="请再次输入新密码"
                          />
                          <button
                            type="button"
                            @click="showConfirmPassword = !showConfirmPassword"
                            class="absolute right-[8px] top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                          >
                            <span class="material-symbols-outlined text-[17px]">
                              {{ showConfirmPassword ? 'visibility_off' : 'visibility' }}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div v-if="passwordError" class="text-[11px] text-red-500">{{ passwordError }}</div>
                    </div>
                  </div>
                  <div class="flex items-center gap-[8px] ml-[12px]">
                    <button
                      v-if="!isChangingPassword"
                      class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      @click="handleChangePassword"
                    >
                      <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">edit</span>
                    </button>
                    <template v-else>
                      <button
                        class="px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors text-[11px]"
                        @click="handleSavePassword"
                      >
                        保存
                      </button>
                      <button
                        class="px-[12px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-[11px]"
                        @click="handleCancelChangePassword"
                      >
                        取消
                      </button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- 我的团队 -->
          <section>
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white mb-[12px]">我的团队</h3>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-[19px]">
              <!-- 操作按钮 -->
              <div class="flex items-center gap-[12px] mb-[19px]">
                <button
                  @click="handleCreateOrganization"
                  class="flex items-center gap-[8px] px-[12px] py-[8px] rounded-md text-[11px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                >
                  <span class="material-symbols-outlined text-[17px]">add</span>
                  <span>创建团队</span>
                </button>
                <button
                  @click="handleJoinOrganization"
                  class="flex items-center gap-[8px] px-[12px] py-[8px] rounded-md text-[11px] font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <span class="material-symbols-outlined text-[17px]">group_add</span>
                  <span>加入团队</span>
                </button>
              </div>

              <!-- 团队列表 -->
              <div v-if="myOrganizations.length > 0" class="space-y-[12px]">
                <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-[12px]">
                  您所属的团队 ({{ myOrganizations.length }})
                </div>
                <div
                  v-for="org in myOrganizations"
                  :key="org.id"
                  class="flex items-center justify-between p-[12px] rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                  @click="handleViewOrganization(org)"
                >
                  <div class="flex items-center gap-[12px]">
                    <!-- 团队图标 -->
                    <div class="w-[37px] h-[37px] rounded-lg bg-primary/10 dark:bg-primary/20 flex items-center justify-center">
                      <span class="material-symbols-outlined text-[19px] text-primary">groups</span>
                    </div>
                    
                    <!-- 团队信息 -->
                    <div>
                      <div class="flex items-center gap-[8px]">
                        <h4 class="font-semibold text-[13px] text-slate-900 dark:text-white">{{ org.name }}</h4>
                        <span
                          v-if="org.role === 'admin'"
                          class="px-[8px] py-[2px] rounded text-[10px] font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400"
                        >
                          管理员
                        </span>
                        <span
                          v-else
                          class="px-[8px] py-[2px] rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                        >
                          成员
                        </span>
                      </div>
                      <div class="flex items-center gap-[12px] mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                        <span class="flex items-center gap-1">
                          <span class="material-symbols-outlined text-[13px]">person</span>
                          {{ org.member_count }} 名成员
                        </span>
                        <span class="flex items-center gap-1">
                          <span class="material-symbols-outlined text-[13px]">calendar_today</span>
                          创建于 {{ new Date(org.created_at).toLocaleDateString() }}
                        </span>
                      </div>
                    </div>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="flex items-center gap-[8px]" @click.stop>
                    <!-- 管理员按钮 -->
                    <template v-if="org.role === 'admin'">
                      <button
                        @click="handleViewOrganization(org)"
                        class="px-[12px] py-[6px] rounded-md text-[11px] font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      >
                        管理成员
                      </button>
                      <button
                        @click="handleDisbandOrganization(org.id)"
                        class="px-[12px] py-[6px] rounded-md text-[11px] font-medium border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      >
                        解散团队
                      </button>
                    </template>
                    <!-- 成员按钮 -->
                    <template v-else>
                       <button
                        @click.stop="handleViewOrganization(org)"
                        class="px-[12px] py-[6px] rounded-md text-[11px] font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      >
                        团队详情
                      </button>
                      <button
                        @click="handleLeaveOrganization(org.id)"
                        class="px-[12px] py-[6px] rounded-md text-[11px] font-medium border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      >
                        离开团队
                      </button>
                    </template>
                  </div>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-else class="text-center py-[37px]">
                <div class="w-[50px] h-[50px] mx-auto mb-[12px] rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-[31px] text-slate-400">groups</span>
                </div>
                <p class="text-[13px] text-slate-600 dark:text-slate-400 mb-[8px]">您还没有加入任何团队</p>
                <p class="text-[11px] text-slate-500 dark:text-slate-500">创建或加入团队，与成员协作管理广告投放</p>
              </div>
            </div>
          </section>

        
        </div>
      </div>
    </main>
  </div>

  <!-- 创建团队弹窗 -->
  <div
    v-if="showCreateOrgDialog"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    @click.self="handleCancelCreateOrg"
  >
    <div class="bg-white dark:bg-slate-800 rounded-md shadow-xl w-full max-w-[625px] mx-4">
      <!-- 弹窗标题 -->
      <div class="flex items-center justify-between p-[19px] border-b border-slate-200 dark:border-slate-700">
        <h3 class="text-[15px] font-semibold text-slate-900 dark:text-white">创建团队</h3>
        <button
          @click="handleCancelCreateOrg"
          class="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">close</span>
        </button>
      </div>

      <!-- 表单内容 -->
      <div class="p-[19px] space-y-[12px]">
        <!-- 团队名称 -->
        <div>
          <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[8px]">
            团队名称 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="createOrgForm.name"
            type="text"
            class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
            placeholder="请输入团队名称"
          />
        </div>

        <!-- 团队 ID -->
        <div>
          <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[8px]">
            团队 ID <span class="text-red-500">*</span>
          </label>
          <input
            v-model="createOrgForm.orgId"
            type="text"
            class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
            placeholder="请输入团队 ID（英文字母、数字、下划线）"
          />
          <p class="mt-1 text-[10px] text-slate-500 dark:text-slate-400">团队 ID 用于邀请成员加入，创建后不可修改</p>
        </div>

        <!-- 团队描述 -->
        <div>
          <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[8px]">
            团队描述
          </label>
          <textarea
            v-model="createOrgForm.description"
            rows="3"
            class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary resize-none text-[13px]"
            placeholder="请输入团队描述（可选）"
          ></textarea>
        </div>

        <!-- 错误提示 -->
        <div v-if="createOrgError" class="text-[11px] text-red-500">{{ createOrgError }}</div>
      </div>

      <!-- 底部按钮 -->
      <div class="flex items-center justify-end gap-[12px] p-[19px] border-t border-slate-200 dark:border-slate-700">
        <button
          @click="handleCancelCreateOrg"
          class="px-[12px] py-[8px] rounded-md text-[11px] font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          取消
        </button>
        <button
          @click="handleSubmitCreateOrg"
          class="px-[12px] py-[8px] rounded-md text-[11px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
        >
          创建团队
        </button>
      </div>
    </div>
  </div>

  <!-- 加入团队弹窗 -->
  <div
    v-if="showJoinOrgDialog"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    @click.self="handleCancelJoinOrg"
  >
    <div class="bg-white dark:bg-slate-800 rounded-md shadow-xl w-full max-w-[344px] mx-4">
      <!-- 弹窗标题 -->
      <div class="flex items-center justify-between p-[19px] border-b border-slate-200 dark:border-slate-700">
        <h3 class="text-[15px] font-semibold text-slate-900 dark:text-white">加入团队</h3>
        <button
          @click="handleCancelJoinOrg"
          class="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">close</span>
        </button>
      </div>

      <!-- 表单内容 -->
      <div class="p-[19px] space-y-[12px]">
        <!-- 团队 ID -->
        <div>
          <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[8px]">
            团队 ID <span class="text-red-500">*</span>
          </label>
          <input
            v-model="joinOrgForm.orgId"
            type="text"
            class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
            placeholder="请输入团队 ID"
          />
        </div>

        <!-- 邀请码 -->
        <div>
          <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[8px]">
            邀请码 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="joinOrgForm.inviteCode"
            type="text"
            class="w-full px-[12px] py-[8px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary text-[13px]"
            placeholder="请输入邀请码"
          />
          <p class="mt-1 text-[10px] text-slate-500 dark:text-slate-400">请向团队管理员获取邀请码</p>
        </div>

        <!-- 错误提示 -->
        <div v-if="joinOrgError" class="text-[11px] text-red-500">{{ joinOrgError }}</div>
      </div>

      <!-- 底部按钮 -->
      <div class="flex items-center justify-end gap-[12px] p-[19px] border-t border-slate-200 dark:border-slate-700">
        <button
          @click="handleCancelJoinOrg"
          class="px-[12px] py-[8px] rounded-md text-[11px] font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          取消
        </button>
        <button
          @click="handleSubmitJoinOrg"
          class="px-[12px] py-[8px] rounded-md text-[11px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
        >
          加入团队
        </button>
      </div>
    </div>
  </div>

  <!-- 确认对话框 -->
  <ConfirmDialog
    :show="showConfirmDialog"
    :title="confirmDialogConfig.title"
    :message="confirmDialogConfig.message"
    :confirm-text="confirmDialogConfig.confirmText"
    :confirm-button-class="confirmDialogConfig.confirmButtonClass"
    @confirm="handleConfirmDialogConfirm"
    @cancel="handleConfirmDialogClose"
    @close="handleConfirmDialogClose"
  />

  <!-- 团队详情弹窗 -->
  <OrganizationDetail
    :show="showOrgDetailDialog"
    :organization="selectedOrganization"
    @close="handleCloseOrgDetail"
    @refresh="handleRefreshOrganizations"
  />

  <!-- Toast 提示容器 -->
  <ToastContainer />
</template>
