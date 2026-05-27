<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'
import { userApi } from '@/api/user'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
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
const myOrganizations = ref([
  {
    id: 'org_001',
    name: 'ACME 营销团队',
    role: 'admin',
    memberCount: 5,
    createdAt: '2024-01-15'
  },
  {
    id: 'org_002',
    name: '东南亚推广组',
    role: 'member',
    memberCount: 3,
    createdAt: '2024-02-20'
  }
])

const handleCreateOrganization = () => {
  console.log('创建团队')
  // TODO: 打开创建团队对话框
}

const handleJoinOrganization = () => {
  console.log('加入团队')
  // TODO: 打开加入团队对话框
}

const handleViewOrganization = (orgId: string) => {
  console.log('查看团队:', orgId)
  // TODO: 跳转到团队详情页面
}

onMounted(() => {
  console.log('账号配置页面加载')
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">系统账号设置</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">管理团队成员、登录身份和基础账号信息</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div class="space-y-6">
          <!-- 登录账户信息 -->
          <section>
            <h3 class="text-base font-semibold text-slate-900 dark:text-white mb-3">登录账户信息</h3>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-6 space-y-4">
              <!-- Email（只读） -->
              <div class="pb-4 border-b border-slate-200 dark:border-slate-700">
                <div class="text-sm text-slate-500 dark:text-slate-400 mb-1">邮箱地址</div>
                <div class="text-base font-medium text-slate-900 dark:text-white">{{ userEmail }}</div>
                <!-- <div class="text-xs text-slate-400 dark:text-slate-500 mt-1">邮箱地址不可修改</div>  -->
              </div>

              <!-- 用户名（可编辑） -->
              <div class="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-700">
                <div class="flex-1">
                  <div class="text-sm text-slate-500 dark:text-slate-400 mb-1">用户名</div>
                  <div v-if="!isEditingName" class="text-base font-medium text-slate-900 dark:text-white">{{ userName }}</div>
                  <input
                    v-else
                    v-model="newName"
                    type="text"
                    class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="请输入新用户名"
                  />
                </div>
                <div class="flex items-center gap-2 ml-4">
                  <button
                    v-if="!isEditingName"
                    class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    @click="handleEditName"
                  >
                    <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-xl">edit</span>
                  </button>
                  <template v-else>
                    <button
                      class="px-3 py-1.5 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors text-sm"
                      @click="handleSaveName"
                    >
                      保存
                    </button>
                    <button
                      class="px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-sm"
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
                    <div class="text-sm text-slate-500 dark:text-slate-400 mb-1">密码</div>
                    <div v-if="!isChangingPassword" class="text-base font-medium text-slate-900 dark:text-white">••••••••</div>
                    
                    <!-- 密码修改表单 -->
                    <div v-else class="space-y-3 mt-2">
                      <div>
                        <label class="block text-sm text-slate-600 dark:text-slate-400 mb-1">当前密码</label>
                        <input
                          v-model="passwordForm.currentPassword"
                          type="password"
                          class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                          placeholder="请输入当前密码"
                        />
                      </div>
                      <div>
                        <label class="block text-sm text-slate-600 dark:text-slate-400 mb-1">新密码</label>
                        <div class="relative">
                          <input
                            v-model="passwordForm.newPassword"
                            :type="showNewPassword ? 'text' : 'password'"
                            class="w-full px-3 py-2 pr-10 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                            placeholder="请输入新密码（至少6个字符）"
                          />
                          <button
                            type="button"
                            @click="showNewPassword = !showNewPassword"
                            class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                          >
                            <span class="material-symbols-outlined text-xl">
                              {{ showNewPassword ? 'visibility_off' : 'visibility' }}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div>
                        <label class="block text-sm text-slate-600 dark:text-slate-400 mb-1">确认新密码</label>
                        <div class="relative">
                          <input
                            v-model="passwordForm.confirmPassword"
                            :type="showConfirmPassword ? 'text' : 'password'"
                            class="w-full px-3 py-2 pr-10 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                            placeholder="请再次输入新密码"
                          />
                          <button
                            type="button"
                            @click="showConfirmPassword = !showConfirmPassword"
                            class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                          >
                            <span class="material-symbols-outlined text-xl">
                              {{ showConfirmPassword ? 'visibility_off' : 'visibility' }}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div v-if="passwordError" class="text-sm text-red-500">{{ passwordError }}</div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 ml-4">
                    <button
                      v-if="!isChangingPassword"
                      class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      @click="handleChangePassword"
                    >
                      <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-xl">edit</span>
                    </button>
                    <template v-else>
                      <button
                        class="px-3 py-1.5 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors text-sm"
                        @click="handleSavePassword"
                      >
                        保存
                      </button>
                      <button
                        class="px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-sm"
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
            <h3 class="text-base font-semibold text-slate-900 dark:text-white mb-3">我的团队</h3>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-6">
              <!-- 操作按钮 -->
              <div class="flex items-center gap-3 mb-6">
                <button
                  @click="handleCreateOrganization"
                  class="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                >
                  <span class="material-symbols-outlined text-xl">add</span>
                  <span>创建团队</span>
                </button>
                <button
                  @click="handleJoinOrganization"
                  class="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <span class="material-symbols-outlined text-xl">group_add</span>
                  <span>加入团队</span>
                </button>
              </div>

              <!-- 团队列表 -->
              <div v-if="myOrganizations.length > 0" class="space-y-3">
                <div class="text-sm text-slate-500 dark:text-slate-400 mb-3">
                  您所属的团队 ({{ myOrganizations.length }})
                </div>
                <div
                  v-for="org in myOrganizations"
                  :key="org.id"
                  class="flex items-center justify-between p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                  @click="handleViewOrganization(org.id)"
                >
                  <div class="flex items-center gap-4">
                    <!-- 团队图标 -->
                    <div class="w-12 h-12 rounded-lg bg-primary/10 dark:bg-primary/20 flex items-center justify-center">
                      <span class="material-symbols-outlined text-2xl text-primary">groups</span>
                    </div>
                    
                    <!-- 团队信息 -->
                    <div>
                      <div class="flex items-center gap-2">
                        <h4 class="font-semibold text-slate-900 dark:text-white">{{ org.name }}</h4>
                        <span
                          v-if="org.role === 'admin'"
                          class="px-2 py-0.5 rounded text-xs font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400"
                        >
                          管理员
                        </span>
                        <span
                          v-else
                          class="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                        >
                          成员
                        </span>
                      </div>
                      <div class="flex items-center gap-4 mt-1 text-sm text-slate-500 dark:text-slate-400">
                        <span class="flex items-center gap-1">
                          <span class="material-symbols-outlined text-base">person</span>
                          {{ org.memberCount }} 名成员
                        </span>
                        <span class="flex items-center gap-1">
                          <span class="material-symbols-outlined text-base">calendar_today</span>
                          创建于 {{ org.createdAt }}
                        </span>
                      </div>
                    </div>
                  </div>

                  <!-- 查看按钮 -->
                  <button
                    class="p-2 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    @click.stop="handleViewOrganization(org.id)"
                  >
                    <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_forward</span>
                  </button>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-else class="text-center py-12">
                <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-4xl text-slate-400">groups</span>
                </div>
                <p class="text-slate-600 dark:text-slate-400 mb-2">您还没有加入任何团队</p>
                <p class="text-sm text-slate-500 dark:text-slate-500">创建或加入团队，与成员协作管理广告投放</p>
              </div>
            </div>
          </section>

        
        </div>
      </div>
    </main>
  </div>

  <!-- Toast 提示容器 -->
  <ToastContainer />
</template>
