<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="show"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click="handleBackdropClick"
      >
        <Transition name="scale">
          <div
            v-if="show"
            class="bg-white dark:bg-slate-800 rounded-md shadow-2xl w-full max-w-4xl mx-4 h-[900px] overflow-hidden border border-slate-200 dark:border-slate-700 flex flex-col"
            @click.stop
          >
            <!-- 头部 -->
            <div class="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
              <h2 class="text-lg font-semibold text-slate-900 dark:text-white">团队详情</h2>
              <button
                @click="handleClose"
                class="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                <span class="material-symbols-outlined text-slate-500 dark:text-slate-400 text-xl">close</span>
              </button>
            </div>

            <!-- 内容区域 -->
            <div class="flex-1 overflow-y-auto p-5 space-y-4">
              <!-- 团队详情模块 -->
              <div class="bg-slate-50 dark:bg-slate-900/30 rounded-md p-4">
                <h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3">团队信息</h3>
                
                <div class="grid grid-cols-3 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <label class="text-xs text-slate-500 dark:text-slate-400">团队名称</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-0.5">{{ organization?.name }}</p>
                  </div>
                  
                  <div>
                    <label class="text-xs text-slate-500 dark:text-slate-400">团队代码</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-0.5">{{ organization?.org_code }}</p>
                  </div>
                  
                  <div>
                    <label class="text-xs text-slate-500 dark:text-slate-400">成员数量</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-0.5">{{ organization?.member_count }} 人</p>
                  </div>
                  
                  <div class="col-span-2">
                    <label class="text-xs text-slate-500 dark:text-slate-400">团队描述</label>
                    <p class="text-slate-700 dark:text-slate-300 mt-0.5">
                      {{ organization?.description || '暂无描述' }}
                    </p>
                  </div>
                  
                  <div>
                    <label class="text-xs text-slate-500 dark:text-slate-400">创建时间</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-0.5">
                      {{ formatDate(organization?.created_at) }}
                    </p>
                  </div>
                  
                  <div v-if="isAdmin" class="col-span-3 mt-1">
                    <label class="text-xs text-slate-500 dark:text-slate-400">邀请码</label>
                    <div class="flex items-center gap-2 mt-0.5">
                      <code class="flex-1 px-2 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md text-xs font-mono text-slate-900 dark:text-white">
                        {{ inviteCode || '加载中...' }}
                      </code>
                      <button
                        v-if="inviteCode"
                        @click="copyInviteCode"
                        class="px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                      >
                        复制
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 团队成员模块 -->
              <div class="bg-slate-50 dark:bg-slate-900/30 rounded-md p-4 flex-1 flex flex-col min-h-0">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-3">
                    <h3 class="text-sm font-semibold text-slate-900 dark:text-white">团队成员</h3>
                    <button
                      v-if="isAdmin"
                      @click="showAddMemberDialog = true"
                      class="flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                    >
                      <span class="material-symbols-outlined text-base">add</span>
                      添加成员
                    </button>
                  </div>
                  
                  <!-- 搜索框 -->
                  <div class="relative w-48">
                    <input
                      v-model="searchQuery"
                      type="text"
                      placeholder="搜索成员..."
                      class="w-full px-3 py-1.5 pl-8 rounded-md text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-primary"
                      @input="handleSearch"
                    >
                    <span class="material-symbols-outlined absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-lg">
                      search
                    </span>
                  </div>
                </div>

                <!-- 成员表格 -->
                <div v-if="loading" class="flex-1 flex items-center justify-center">
                  <div class="text-center">
                    <div class="inline-block animate-spin rounded-full h-6 w-6 border-2 border-primary border-t-transparent"></div>
                    <p class="text-slate-500 dark:text-slate-400 text-sm mt-2">加载中...</p>
                  </div>
                </div>

                <div v-else-if="members.length === 0" class="flex-1 flex items-center justify-center">
                  <div class="text-center">
                    <span class="material-symbols-outlined text-slate-300 dark:text-slate-600 text-4xl">group_off</span>
                    <p class="text-slate-500 dark:text-slate-400 text-sm mt-2">暂无成员</p>
                  </div>
                </div>

                <div v-else class="flex-1 overflow-auto">
                  <table class="w-full text-sm">
                    <thead class="bg-white dark:bg-slate-800 sticky top-0">
                      <tr class="border-b border-slate-200 dark:border-slate-700">
                        <th class="text-left py-2 px-3 font-medium text-slate-700 dark:text-slate-300">成员</th>
                        <th class="text-left py-2 px-3 font-medium text-slate-700 dark:text-slate-300">邮箱</th>
                        <th class="text-left py-2 px-3 font-medium text-slate-700 dark:text-slate-300">角色</th>
                        <th class="text-left py-2 px-3 font-medium text-slate-700 dark:text-slate-300">加入时间</th>
                        <th v-if="isAdmin" class="text-right py-2 px-3 font-medium text-slate-700 dark:text-slate-300">操作</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white dark:bg-slate-800">
                      <tr
                        v-for="member in members"
                        :key="member.id"
                        class="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
                      >
                        <td class="py-2 px-3">
                          <div class="flex items-center gap-2">
                            <div class="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                              <span class="material-symbols-outlined text-primary text-base">person</span>
                            </div>
                            <span class="font-medium text-slate-900 dark:text-white">{{ member.user_name }}</span>
                          </div>
                        </td>
                        <td class="py-2 px-3 text-slate-600 dark:text-slate-400">{{ member.user_email }}</td>
                        <td class="py-2 px-3">
                          <span
                            :class="[
                              'px-2 py-0.5 rounded-md text-xs font-medium',
                              member.role === 'admin' 
                                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                            ]"
                          >
                            {{ member.role === 'admin' ? '管理员' : '成员' }}
                          </span>
                        </td>
                        <td class="py-2 px-3 text-slate-600 dark:text-slate-400">{{ formatDate(member.joined_at) }}</td>
                        <td v-if="isAdmin" class="py-2 px-3 text-right">
                          <button
                            v-if="member.role !== 'admin'"
                            @click="handleRemoveMember(member)"
                            class="p-1 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition-colors"
                            title="移除成员"
                          >
                            <span class="material-symbols-outlined text-lg">person_remove</span>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 分页 -->
                <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                  <button
                    @click="handlePrevPage"
                    :disabled="currentPage === 1"
                    class="px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span class="material-symbols-outlined text-lg">chevron_left</span>
                  </button>
                  
                  <span class="text-xs text-slate-600 dark:text-slate-400">
                    第 {{ currentPage }} / {{ totalPages }} 页
                  </span>
                  
                  <button
                    @click="handleNextPage"
                    :disabled="currentPage === totalPages"
                    class="px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span class="material-symbols-outlined text-lg">chevron_right</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- 添加成员弹窗 -->
    <Transition name="fade">
      <div
        v-if="showAddMemberDialog"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click="showAddMemberDialog = false"
      >
        <Transition name="scale">
          <div
            v-if="showAddMemberDialog"
            class="bg-white dark:bg-slate-800 rounded-md shadow-2xl w-full max-w-md mx-4 p-5 border border-slate-200 dark:border-slate-700"
            @click.stop
          >
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">添加成员</h3>
            
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  成员邮箱
                </label>
                <input
                  v-model="addMemberEmail"
                  type="email"
                  placeholder="请输入成员邮箱地址"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary"
                  @keyup.enter="handleAddMember"
                />
                <p v-if="addMemberError" class="text-red-500 text-sm mt-1">{{ addMemberError }}</p>
              </div>
              
              <div class="flex justify-end gap-2">
                <button
                  @click="showAddMemberDialog = false"
                  class="px-4 py-2 rounded-md text-sm font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  取消
                </button>
                <button
                  @click="handleAddMember"
                  class="px-4 py-2 rounded-md text-sm font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                >
                  添加
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

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
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { organizationApi, type OrganizationResponse, type OrganizationMember } from '../../api/organization'
import { useToast } from '@/composables/useToast'
import ConfirmDialog from '../toasts/ConfirmDialog.vue'

const { success, error: showError } = useToast()

type Member = OrganizationMember

interface Props {
  show: boolean
  organization: OrganizationResponse | null
}

interface Emits {
  (e: 'close'): void
  (e: 'refresh'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const loading = ref(false)
const members = ref<Member[]>([])
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = 10
const totalMembers = ref(0)
const inviteCode = ref('')

// 添加成员弹窗
const showAddMemberDialog = ref(false)
const addMemberEmail = ref('')
const addMemberError = ref('')

// 确认对话框
const showConfirmDialog = ref(false)
const confirmDialogConfig = ref({
  title: '',
  message: '',
  confirmText: '确定',
  confirmButtonClass: 'bg-red-500 hover:bg-red-600',
  onConfirm: () => {}
})

const isAdmin = computed(() => props.organization?.role === 'admin')
const totalPages = computed(() => Math.ceil(totalMembers.value / pageSize))

const handleBackdropClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) {
    handleClose()
  }
}

const handleClose = () => {
  emit('close')
}

const formatDate = (dateString: string | undefined) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const loadMembers = async () => {
  if (!props.organization) return
  
  loading.value = true
  try {
    const response = await organizationApi.getMembers(props.organization.id, {
      page: currentPage.value,
      page_size: pageSize,
      search: searchQuery.value || undefined
    })
    
    members.value = response.members
    totalMembers.value = response.total
  } catch (error) {
    console.error('加载成员列表失败:', error)
    members.value = []
    totalMembers.value = 0
  } finally {
    loading.value = false
  }
}

const loadInviteCode = async () => {
  if (!props.organization || !isAdmin.value) return
  
  try {
    const response = await organizationApi.getInviteCode(props.organization.id)
    inviteCode.value = response.invite_code
  } catch (error) {
    console.error('获取邀请码失败:', error)
    inviteCode.value = ''
  }
}

const copyInviteCode = async () => {
  try {
    await navigator.clipboard.writeText(inviteCode.value)
    // TODO: 显示成功提示
    alert('邀请码已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadMembers()
}

const handlePrevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    loadMembers()
  }
}

const handleNextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    loadMembers()
  }
}

const handleAddMember = async () => {
  addMemberError.value = ''
  
  if (!addMemberEmail.value.trim()) {
    addMemberError.value = '请输入成员邮箱'
    return
  }
  
  // 简单的邮箱格式验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(addMemberEmail.value)) {
    addMemberError.value = '请输入有效的邮箱地址'
    return
  }
  
  try {
    await organizationApi.addMember(props.organization!.id, addMemberEmail.value)
    
    success('成员添加成功')
    showAddMemberDialog.value = false
    addMemberEmail.value = ''
    loadMembers()
    emit('refresh')
  } catch (error: any) {
    console.error('添加成员失败:', error)
    addMemberError.value = error.response?.data?.detail || '添加成员失败，请稍后重试'
  }
}

const handleRemoveMember = (member: Member) => {
  confirmDialogConfig.value = {
    title: '移除成员',
    message: `确定要移除成员「${member.user_name}」吗？此操作无法撤销。`,
    confirmText: '移除',
    confirmButtonClass: 'bg-red-500 hover:bg-red-600',
    onConfirm: async () => {
      try {
        await organizationApi.removeMember(props.organization!.id, member.user_id)
        
        success('成员已移除')
        loadMembers()
        emit('refresh')
      } catch (error: any) {
        console.error('移除成员失败:', error)
        showError(error.response?.data?.detail || '移除成员失败，请稍后重试')
      }
    }
  }
  showConfirmDialog.value = true
}

const handleConfirmDialogConfirm = () => {
  confirmDialogConfig.value.onConfirm()
  showConfirmDialog.value = false
}

const handleConfirmDialogClose = () => {
  showConfirmDialog.value = false
}

watch(() => props.show, (newShow) => {
  if (newShow && props.organization) {
    currentPage.value = 1
    searchQuery.value = ''
    loadMembers()
    loadInviteCode()
  }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
