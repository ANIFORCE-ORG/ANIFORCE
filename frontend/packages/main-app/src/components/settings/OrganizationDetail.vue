<template>
  <Teleport to="body">
    <div v-if="show" class="settings-modal-layer" @click="handleBackdropClick">
      <section class="settings-modal wide" role="dialog" aria-modal="true" aria-labelledby="team-detail-title" @click.stop>
        <header class="settings-modal-head">
          <h2 id="team-detail-title">团队详情</h2>
          <button class="settings-modal-close" type="button" aria-label="关闭" @click="handleClose">
            <svg class="sn-icon" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg>
          </button>
        </header>
        <div class="settings-modal-body">
          <div class="sn-team-summary">
            <h3>团队信息</h3>
            <div class="sn-summary-grid">
              <div class="sn-summary-item"><span>团队名称</span><strong>{{ organization?.name }}</strong></div>
              <div class="sn-summary-item"><span>团队代码</span><strong>{{ organization?.org_code }}</strong></div>
              <div class="sn-summary-item"><span>成员数量</span><strong>{{ organization?.member_count }} 人</strong></div>
              <div class="sn-summary-item"><span>团队描述</span><strong>{{ organization?.description || '暂无描述' }}</strong></div>
              <div class="sn-summary-item"><span>创建时间</span><strong>{{ formatDate(organization?.created_at) }}</strong></div>
              <div v-if="isAdmin" class="sn-invite-row"><div class="sn-invite-code">{{ inviteCode || '加载中...' }}</div><button class="sn-button primary" type="button" :disabled="!inviteCode" @click="copyInviteCode">复制邀请码</button></div>
            </div>
          </div>

          <div class="sn-members">
            <div class="sn-members-head">
              <div class="sn-members-title">团队成员 <button v-if="isAdmin" class="sn-button primary" type="button" @click="showAddMemberDialog = true"><svg class="sn-icon" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>添加成员</button></div>
              <input v-model="searchQuery" class="sn-search" placeholder="搜索成员…" @input="handleSearch" />
            </div>

            <div v-if="loading" class="sn-loading">加载中...</div>
            <div v-else-if="members.length === 0" class="sn-loading">暂无成员</div>
            <div v-else class="sn-table-wrap">
              <table class="sn-member-table">
                <thead><tr><th>成员</th><th>邮箱</th><th>角色</th><th>加入时间</th><th v-if="isAdmin">操作</th></tr></thead>
                <tbody>
                  <tr v-for="member in members" :key="member.id">
                    <td><span class="sn-member-name"><span class="sn-mini-avatar"><svg class="sn-icon" viewBox="0 0 24 24"><circle cx="12" cy="8" r="3" /><path d="M5 20c0-4 2.8-6 7-6s7 2 7 6" /></svg></span>{{ member.user_name }}</span></td>
                    <td>{{ member.user_email }}</td>
                    <td><span class="sn-badge" :class="{ 'role-admin': member.role === 'admin' }">{{ member.role === 'admin' ? '管理员' : '成员' }}</span></td>
                    <td>{{ formatDate(member.joined_at) }}</td>
                    <td v-if="isAdmin"><button v-if="member.role !== 'admin'" class="sn-icon-button" type="button" aria-label="移除成员" @click="handleRemoveMember(member)"><svg class="sn-icon" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3" /><path d="M3 19c0-3.2 2.4-5 6-5 1.5 0 2.8.3 3.8.9M16 12h6" /></svg></button><span v-else>—</span></td>
                  </tr>
                </tbody>
              </table>
              <div v-if="totalPages > 1" class="sn-pagination"><button class="sn-button" type="button" :disabled="currentPage === 1" @click="handlePrevPage">上一页</button><span>第 {{ currentPage }} / {{ totalPages }} 页</span><button class="sn-button" type="button" :disabled="currentPage === totalPages" @click="handleNextPage">下一页</button></div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div v-if="showAddMemberDialog" class="settings-modal-layer" style="z-index:120" @click.self="showAddMemberDialog = false">
      <section class="settings-modal compact" role="dialog" aria-modal="true" aria-labelledby="add-member-title">
        <header class="settings-modal-head"><h2 id="add-member-title">添加成员</h2><button class="settings-modal-close" type="button" aria-label="关闭" @click="showAddMemberDialog = false"><svg class="sn-icon" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button></header>
        <div class="settings-modal-body"><div class="sn-input-group"><label>成员邮箱 *</label><input v-model="addMemberEmail" class="sn-input" type="email" placeholder="请输入成员邮箱地址" @keyup.enter="handleAddMember" /><span class="sn-help">成员将收到团队邀请，接受后加入当前团队。</span><span v-if="addMemberError" class="sn-error">{{ addMemberError }}</span></div></div>
        <footer class="settings-modal-actions"><button class="sn-button" type="button" @click="showAddMemberDialog = false">取消</button><button class="sn-button confirm" type="button" @click="handleAddMember">添加成员</button></footer>
      </section>
    </div>
  </Teleport>

  <ConfirmDialog variant="notion" :show="showConfirmDialog" :title="confirmDialogConfig.title" :message="confirmDialogConfig.message" :confirm-text="confirmDialogConfig.confirmText" :confirm-button-class="confirmDialogConfig.confirmButtonClass" @confirm="handleConfirmDialogConfirm" @cancel="handleConfirmDialogClose" @close="handleConfirmDialogClose" />

  <template v-if="false">
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
            class="bg-white dark:bg-slate-800 rounded-md shadow-2xl w-full max-w-[750px] mx-4 h-[702px] overflow-hidden border border-slate-200 dark:border-slate-700 flex flex-col"
            @click.stop
          >
            <!-- 头部 -->
            <div class="flex items-center justify-between px-[16px] py-[9px] border-b border-slate-200 dark:border-slate-700">
              <h2 class="text-[15px] font-semibold text-slate-900 dark:text-white">团队详情</h2>
              <button
                @click="handleClose"
                class="p-[5px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                <span class="material-symbols-outlined text-slate-500 dark:text-slate-400 text-[17px]">close</span>
              </button>
            </div>

            <!-- 内容区域 -->
            <div class="flex-1 overflow-y-auto p-[16px] space-y-[12px]">
              <!-- 团队详情模块 -->
              <div class="bg-slate-50 dark:bg-slate-900/30 rounded-md p-[12px]">
                <h3 class="text-[11px] font-semibold text-slate-900 dark:text-white mb-[9px]">团队信息</h3>
                
                <div class="grid grid-cols-3 gap-x-[12px] gap-y-[6px] text-[11px]">
                  <div>
                    <label class="text-[10px] text-slate-500 dark:text-slate-400">团队名称</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-[2px]">{{ organization?.name }}</p>
                  </div>
                  
                  <div>
                    <label class="text-[10px] text-slate-500 dark:text-slate-400">团队代码</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-[2px]">{{ organization?.org_code }}</p>
                  </div>
                  
                  <div>
                    <label class="text-[10px] text-slate-500 dark:text-slate-400">成员数量</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-[2px]">{{ organization?.member_count }} 人</p>
                  </div>
                  
                  <div class="col-span-2">
                    <label class="text-[10px] text-slate-500 dark:text-slate-400">团队描述</label>
                    <p class="text-slate-700 dark:text-slate-300 mt-[2px]">
                      {{ organization?.description || '暂无描述' }}
                    </p>
                  </div>
                  
                  <div>
                    <label class="text-[10px] text-slate-500 dark:text-slate-400">创建时间</label>
                    <p class="font-medium text-slate-900 dark:text-white mt-[2px]">
                      {{ formatDate(organization?.created_at) }}
                    </p>
                  </div>
                  
                  <div v-if="isAdmin" class="col-span-3 mt-[4px]">
                    <label class="text-[10px] text-slate-500 dark:text-slate-400">邀请码</label>
                    <div class="flex items-center gap-[8px] mt-[2px]">
                      <code class="flex-1 px-[8px] py-[6px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md text-[10px] font-mono text-slate-900 dark:text-white">
                        {{ inviteCode || '加载中...' }}
                      </code>
                      <button
                        v-if="inviteCode"
                        @click="copyInviteCode"
                        class="px-[9px] py-[6px] rounded-md text-[10px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                      >
                        复制
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 团队成员模块 -->
              <div class="bg-slate-50 dark:bg-slate-900/30 rounded-md p-[12px] flex-1 flex flex-col min-h-0">
                <div class="flex items-center justify-between mb-[9px]">
                  <div class="flex items-center gap-[9px]">
                    <h3 class="text-[11px] font-semibold text-slate-900 dark:text-white">团队成员</h3>
                    <button
                      v-if="isAdmin"
                      @click="showAddMemberDialog = true"
                      class="flex items-center gap-[4px] px-[6px] py-[4px] rounded-md text-[10px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                    >
                      <span class="material-symbols-outlined text-[13px]">add</span>
                      添加成员
                    </button>
                  </div>
                  
                  <!-- 搜索框 -->
                  <div class="relative w-[150px]">
                    <input
                      v-model="searchQuery"
                      type="text"
                      placeholder="搜索成员..."
                      class="w-full px-[9px] py-[6px] pl-[25px] rounded-md text-[11px] border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-primary"
                      @input="handleSearch"
                    >
                    <span class="material-symbols-outlined absolute left-[6px] top-1/2 -translate-y-1/2 text-slate-400 text-[15px]">
                      search
                    </span>
                  </div>
                </div>

                <!-- 成员表格 -->
                <div v-if="loading" class="flex-1 flex items-center justify-center">
                  <div class="text-center">
                    <div class="inline-block animate-spin rounded-full h-[19px] w-[19px] border-2 border-primary border-t-transparent"></div>
                    <p class="text-slate-500 dark:text-slate-400 text-[11px] mt-[6px]">加载中...</p>
                  </div>
                </div>

                <div v-else-if="members.length === 0" class="flex-1 flex items-center justify-center">
                  <div class="text-center">
                    <span class="material-symbols-outlined text-slate-300 dark:text-slate-600 text-[31px]">group_off</span>
                    <p class="text-slate-500 dark:text-slate-400 text-[11px] mt-[6px]">暂无成员</p>
                  </div>
                </div>

                <div v-else class="flex-1 overflow-auto">
                  <table class="w-full text-[11px]">
                    <thead class="bg-white dark:bg-slate-800 sticky top-0">
                      <tr class="border-b border-slate-200 dark:border-slate-700">
                        <th class="text-left py-[6px] px-[9px] font-medium text-slate-700 dark:text-slate-300">成员</th>
                        <th class="text-left py-[6px] px-[9px] font-medium text-slate-700 dark:text-slate-300">邮箱</th>
                        <th class="text-left py-[6px] px-[9px] font-medium text-slate-700 dark:text-slate-300">角色</th>
                        <th class="text-left py-[6px] px-[9px] font-medium text-slate-700 dark:text-slate-300">加入时间</th>
                        <th v-if="isAdmin" class="text-right py-[6px] px-[9px] font-medium text-slate-700 dark:text-slate-300">操作</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white dark:bg-slate-800">
                      <tr
                        v-for="member in members"
                        :key="member.id"
                        class="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
                      >
                        <td class="py-[6px] px-[9px]">
                          <div class="flex items-center gap-[6px]">
                            <div class="w-[22px] h-[22px] rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                              <span class="material-symbols-outlined text-primary text-[13px]">person</span>
                            </div>
                            <span class="font-medium text-slate-900 dark:text-white">{{ member.user_name }}</span>
                          </div>
                        </td>
                        <td class="py-[6px] px-[9px] text-slate-600 dark:text-slate-400">{{ member.user_email }}</td>
                        <td class="py-[6px] px-[9px]">
                          <span
                            :class="[
                              'px-[6px] py-[2px] rounded-md text-[10px] font-medium',
                              member.role === 'admin' 
                                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                            ]"
                          >
                            {{ member.role === 'admin' ? '管理员' : '成员' }}
                          </span>
                        </td>
                        <td class="py-[6px] px-[9px] text-slate-600 dark:text-slate-400">{{ formatDate(member.joined_at) }}</td>
                        <td v-if="isAdmin" class="py-[6px] px-[9px] text-right">
                          <button
                            v-if="member.role !== 'admin'"
                            @click="handleRemoveMember(member)"
                            class="p-[4px] rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition-colors"
                            title="移除成员"
                          >
                            <span class="material-symbols-outlined text-[15px]">person_remove</span>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 分页 -->
                <div v-if="totalPages > 1" class="flex items-center justify-center gap-[6px] mt-[9px] pt-[9px] border-t border-slate-200 dark:border-slate-700">
                  <button
                    @click="handlePrevPage"
                    :disabled="currentPage === 1"
                    class="px-[6px] py-[4px] rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span class="material-symbols-outlined text-[15px]">chevron_left</span>
                  </button>
                  
                  <span class="text-[10px] text-slate-600 dark:text-slate-400">
                    第 {{ currentPage }} / {{ totalPages }} 页
                  </span>
                  
                  <button
                    @click="handleNextPage"
                    :disabled="currentPage === totalPages"
                    class="px-[6px] py-[4px] rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span class="material-symbols-outlined text-[15px]">chevron_right</span>
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
            class="bg-white dark:bg-slate-800 rounded-md shadow-2xl w-full max-w-[344px] mx-4 p-[16px] border border-slate-200 dark:border-slate-700"
            @click.stop
          >
            <h3 class="text-[15px] font-semibold text-slate-900 dark:text-white mb-[12px]">添加成员</h3>
            
            <div class="space-y-[12px]">
              <div>
                <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[6px]">
                  成员邮箱
                </label>
                <input
                  v-model="addMemberEmail"
                  type="email"
                  placeholder="请输入成员邮箱地址"
                  class="w-full px-[9px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary text-[11px]"
                  @keyup.enter="handleAddMember"
                />
                <p v-if="addMemberError" class="text-red-500 text-[11px] mt-[4px]">{{ addMemberError }}</p>
              </div>
              
              <div class="flex justify-end gap-[6px]">
                <button
                  @click="showAddMemberDialog = false"
                  class="px-[12px] py-[6px] rounded-md text-[11px] font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  取消
                </button>
                <button
                  @click="handleAddMember"
                  class="px-[12px] py-[6px] rounded-md text-[11px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
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
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { organizationApi, type OrganizationResponse, type OrganizationMember } from '../../api/organization'
import { useToast } from '@/composables/useToast'
import ConfirmDialog from '../toasts/ConfirmDialog.vue'
import '@/styles/settings-notion.css'

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
