<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { organizationApi, type OrganizationResponse } from '@/api/organization'
import { platformApi, type PlatformConnectionResponse } from '@/api/platform'

type GuidePane = 'intro' | 'connect' | 'organization' | 'done'
type SupportedPlatform = 'Meta' | 'Google'

const route = useRoute()
const visible = ref(false)
const pane = ref<GuidePane>('intro')
const loading = ref(false)
const actionLoading = ref<SupportedPlatform | 'organization' | null>(null)
const errorMessage = ref('')
const statusMessage = ref('')
const connections = ref<PlatformConnectionResponse[]>([])
const organizations = ref<OrganizationResponse[]>([])
const orgCode = ref('')
const inviteCode = ref('')

const DISMISSED_KEY = 'aniforce_new_user_guide_dismissed'
const activeConnections = computed(() => connections.value.filter(item => item.status === 'active'))
const configured = computed(() => activeConnections.value.length > 0 || organizations.value.length > 0)
const connectedPlatforms = computed(() => new Set(activeConnections.value.map(item => item.platform.toLowerCase())))

const apiError = (error: unknown, fallback: string) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : error instanceof Error ? error.message : fallback
}

const loadStatus = async (showLoading = true) => {
  if (showLoading) loading.value = true
  errorMessage.value = ''
  try {
    const [connectionRows, organizationRows] = await Promise.all([
      platformApi.getAllConnections(),
      organizationApi.getMyOrganizations(),
    ])
    connections.value = connectionRows
    organizations.value = organizationRows
    if (configured.value && pane.value !== 'intro') pane.value = 'done'
  } catch (error) {
    errorMessage.value = apiError(error, '初始化状态读取失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const openGuide = async () => {
  pane.value = configured.value ? 'done' : 'intro'
  errorMessage.value = ''
  statusMessage.value = ''
  visible.value = true
  await loadStatus()
}

const dismissGuide = () => {
  sessionStorage.setItem(DISMISSED_KEY, 'true')
  visible.value = false
}

const finishGuide = () => {
  if (!configured.value) return
  sessionStorage.removeItem(DISMISSED_KEY)
  visible.value = false
}

const startOAuth = async (platform: SupportedPlatform) => {
  actionLoading.value = platform
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    const response = platform === 'Meta'
      ? await platformApi.startMetaOAuth()
      : await platformApi.startGoogleOAuth()
    const popup = window.open(response.authorize_url, '_blank', 'width=640,height=760')
    if (!popup) throw new Error('浏览器阻止了授权窗口，请允许弹窗后重试')
    statusMessage.value = `${platform} 授权已在新窗口打开。完成后返回此页面，系统会自动检查连接状态。`
  } catch (error) {
    errorMessage.value = apiError(error, `${platform} 授权启动失败`)
  } finally {
    actionLoading.value = null
  }
}

const joinOrganization = async () => {
  const normalizedCode = orgCode.value.trim()
  const normalizedInvite = inviteCode.value.trim()
  if (!normalizedCode || !normalizedInvite) {
    errorMessage.value = '请输入团队 ID 和邀请码'
    return
  }
  actionLoading.value = 'organization'
  errorMessage.value = ''
  try {
    const joined = await organizationApi.join({ org_code: normalizedCode, invite_code: normalizedInvite })
    organizations.value = [joined, ...organizations.value.filter(item => item.id !== joined.id)]
    statusMessage.value = `已加入 ${joined.name}`
    pane.value = 'done'
  } catch (error) {
    errorMessage.value = apiError(error, '加入组织失败，请检查团队 ID 和邀请码')
  } finally {
    actionLoading.value = null
  }
}

const refreshConnectionStatus = async () => {
  await loadStatus()
  if (!configured.value && !errorMessage.value) statusMessage.value = '暂未检测到已完成的授权，请确认平台授权窗口中的操作已完成。'
}

const handleWindowFocus = () => {
  if (visible.value && pane.value === 'connect' && statusMessage.value) void loadStatus(false)
}
const handleOpenEvent = () => { void openGuide() }
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && visible.value) dismissGuide()
}

watch(visible, value => document.body.classList.toggle('guide-modal-open', value))
watch(() => route.query.guide, value => { if (value === '1') void openGuide() })

onMounted(async () => {
  window.addEventListener('focus', handleWindowFocus)
  window.addEventListener('aniforce:open-new-user-guide', handleOpenEvent)
  document.addEventListener('keydown', handleKeydown)
  await loadStatus()
  const debugRequested = route.query.guide === '1'
  const dismissed = sessionStorage.getItem(DISMISSED_KEY) === 'true'
  if (debugRequested || (!configured.value && !dismissed)) visible.value = true
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', handleWindowFocus)
  window.removeEventListener('aniforce:open-new-user-guide', handleOpenEvent)
  document.removeEventListener('keydown', handleKeydown)
  document.body.classList.remove('guide-modal-open')
})
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="guide-backdrop" role="dialog" aria-modal="true" aria-labelledby="new-user-guide-title">
      <section class="guide-modal">
        <button class="guide-close" type="button" aria-label="关闭新手引导" @click="dismissGuide"><span class="material-symbols-outlined">close</span></button>

        <header class="guide-head">
          <div>
            <span class="guide-kicker"><span class="material-symbols-outlined">route</span>工作区初始化</span>
            <h2 id="new-user-guide-title">{{ pane === 'done' ? '工作区已准备好' : '先完成一项基础配置' }}</h2>
            <p>{{ pane === 'done' ? '以下状态来自当前账户的真实连接和组织信息。' : '连接广告渠道或加入已有组织，之后即可使用对应的数据和团队配置。' }}</p>
          </div>
          <div class="guide-progress"><strong>{{ pane === 'intro' ? '1' : '2' }} / 2</strong><span><i :style="{ width: pane === 'intro' ? '50%' : '100%' }"></i></span></div>
        </header>

        <div v-if="loading" class="guide-loading" role="status"><span class="material-symbols-outlined">progress_activity</span>正在读取账户配置...</div>

        <template v-else>
          <div v-if="pane === 'intro'" class="guide-body">
            <div class="guide-choice-grid">
              <button class="guide-choice" type="button" @click="pane = 'connect'">
                <span class="guide-choice-icon"><span class="material-symbols-outlined">sync_alt</span></span>
                <span class="guide-recommend">推荐</span>
                <strong>连接广告渠道</strong>
                <p>通过官方 OAuth 授权 Meta 或 Google，读取账户、计划和真实投放数据。</p>
                <span class="guide-choice-action">开始连接 <span class="material-symbols-outlined">arrow_forward</span></span>
              </button>
              <button class="guide-choice" type="button" @click="pane = 'organization'">
                <span class="guide-choice-icon warm"><span class="material-symbols-outlined">group_add</span></span>
                <strong>加入已有组织</strong>
                <p>使用团队 ID 和邀请码加入现有工作区，共享团队配置和业务资源。</p>
                <span class="guide-choice-action">输入邀请码 <span class="material-symbols-outlined">arrow_forward</span></span>
              </button>
              <button class="guide-choice" type="button" @click="dismissGuide">
                <span class="guide-choice-icon neutral"><span class="material-symbols-outlined">schedule</span></span>
                <strong>稍后配置</strong>
                <p>先进入工作区查看现有功能。本次会话不再提示，之后可从侧栏重新打开。</p>
                <span class="guide-choice-action muted">进入工作区</span>
              </button>
            </div>
          </div>

          <div v-else-if="pane === 'connect'" class="guide-body compact">
            <div class="guide-step-bar"><button type="button" @click="pane = 'intro'"><span class="material-symbols-outlined">arrow_back</span>返回</button><button type="button" @click="refreshConnectionStatus">刷新状态</button></div>
            <div class="guide-channel-list">
              <article class="guide-channel-row">
                <span class="guide-channel-mark meta">M</span><div><strong>Meta Ads</strong><p>连接 Meta Business 和广告账户。</p></div>
                <span v-if="connectedPlatforms.has('meta')" class="guide-connected"><span class="material-symbols-outlined">check</span>已连接</span>
                <button v-else type="button" :disabled="Boolean(actionLoading)" @click="startOAuth('Meta')">{{ actionLoading === 'Meta' ? '启动中...' : '连接' }}</button>
              </article>
              <article class="guide-channel-row">
                <span class="guide-channel-mark google">G</span><div><strong>Google Ads</strong><p>连接 Google Ads 客户账户。</p></div>
                <span v-if="connectedPlatforms.has('google')" class="guide-connected"><span class="material-symbols-outlined">check</span>已连接</span>
                <button v-else type="button" :disabled="Boolean(actionLoading)" @click="startOAuth('Google')">{{ actionLoading === 'Google' ? '启动中...' : '连接' }}</button>
              </article>
              <article class="guide-channel-row disabled">
                <span class="guide-channel-mark tiktok">T</span><div><strong>TikTok Ads</strong><p>平台授权链路尚未接入。</p></div><span class="guide-unavailable">即将支持</span>
              </article>
            </div>
          </div>

          <div v-else-if="pane === 'organization'" class="guide-body compact">
            <div class="guide-step-bar"><button type="button" @click="pane = 'intro'"><span class="material-symbols-outlined">arrow_back</span>返回</button></div>
            <form class="guide-org-form" @submit.prevent="joinOrganization">
              <div><h3>加入团队工作区</h3><p>信息会提交到现有组织服务进行校验，不会在浏览器中模拟加入结果。</p></div>
              <label><span>团队 ID</span><input v-model="orgCode" autocomplete="organization" placeholder="请输入团队 ID"></label>
              <label><span>邀请码</span><input v-model="inviteCode" autocomplete="off" placeholder="请输入邀请码"></label>
              <button type="submit" :disabled="Boolean(actionLoading)">{{ actionLoading === 'organization' ? '正在申请...' : '申请加入' }}</button>
            </form>
          </div>

          <div v-else class="guide-body compact">
            <div class="guide-done">
              <span class="guide-done-mark"><span class="material-symbols-outlined">check</span></span>
              <h3>初始化状态已确认</h3>
              <p>系统只展示后端已经确认的连接和组织，不会把未完成的授权标记为成功。</p>
              <dl>
                <div><dt>广告渠道</dt><dd>{{ activeConnections.length ? activeConnections.map(item => item.platform).join('、') : '尚未连接' }}</dd></div>
                <div><dt>所属组织</dt><dd>{{ organizations.length ? organizations.map(item => item.name).join('、') : '尚未加入' }}</dd></div>
              </dl>
              <button type="button" :disabled="!configured" @click="finishGuide">进入 ANIFORCE 工作区</button>
            </div>
          </div>

          <p v-if="errorMessage" class="guide-message error" role="alert">{{ errorMessage }}</p>
          <p v-else-if="statusMessage" class="guide-message" role="status">{{ statusMessage }}</p>
        </template>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
:global(body.guide-modal-open) { overflow: hidden; }
.guide-backdrop { position: fixed; z-index: 1000; inset: 0; display: grid; place-items: center; padding: 24px; background: rgb(15 15 15 / 28%); backdrop-filter: blur(6px); color: #37352f; font-family: "Notion Sans", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; }
.guide-modal { position: relative; width: min(960px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); overflow: auto; border: 1px solid #e5e3df; border-radius: 10px; background: #fff; box-shadow: 0 24px 72px rgb(15 15 15 / 18%); }
.guide-close { position: absolute; z-index: 2; top: 12px; right: 12px; width: 32px; height: 32px; display: grid; place-items: center; border: 0; border-radius: 6px; background: transparent; color: #787671; cursor: pointer; }.guide-close:hover { background: #f1f1ef; color: #37352f; }.guide-close span { font-size: 18px; }
.guide-head { display: grid; grid-template-columns: minmax(0,1fr) 150px; align-items: center; gap: 24px; padding: 22px 26px; border-bottom: 1px solid #e9e9e7; }.guide-kicker { min-height: 25px; display: inline-flex; align-items: center; gap: 6px; padding: 0 8px; border-radius: 5px; background: #eaf3fb; color: #2383e2; font-size: 11px; font-weight: 650; }.guide-kicker span { font-size: 15px; }.guide-head h2 { margin: 10px 0 5px; color: #20201e; font-size: 20px; letter-spacing: 0; }.guide-head p { margin: 0; color: #787774; font-size: 12px; line-height: 1.55; }.guide-progress strong { display: block; margin-bottom: 8px; font-size: 11px; }.guide-progress > span { display: block; height: 5px; overflow: hidden; border-radius: 99px; background: #efefed; }.guide-progress i { display: block; height: 100%; background: #2383e2; transition: width .2s ease; }
.guide-body { padding: 20px 26px 24px; }.guide-body.compact { padding-top: 14px; }.guide-choice-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; }.guide-choice { position: relative; min-height: 250px; display: flex; align-items: flex-start; flex-direction: column; gap: 14px; padding: 18px; border: 1px solid #e5e3df; border-radius: 8px; background: #fff; color: #37352f; text-align: left; cursor: pointer; }.guide-choice:hover { border-color: #c8c4be; background: #fafaf9; }.guide-choice-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 8px; background: #eaf3fb; color: #2383e2; }.guide-choice-icon.warm { background: #f5eeee; color: #9f6b53; }.guide-choice-icon.neutral { background: #fbf3db; color: #906b18; }.guide-choice-icon span { font-size: 22px; }.guide-choice strong { color: #20201e; font-size: 15px; }.guide-choice p { margin: 0; color: #787774; font-size: 12px; line-height: 1.6; }.guide-recommend { position: absolute; top: 18px; right: 18px; padding: 3px 7px; border-radius: 5px; background: #edf5ee; color: #2f6b3c; font-size: 10px; }.guide-choice-action { display: inline-flex; align-items: center; gap: 5px; margin-top: auto; color: #2383e2; font-size: 11px; font-weight: 650; }.guide-choice-action span { font-size: 15px; }.guide-choice-action.muted { color: #787774; }
.guide-loading { min-height: 300px; display: flex; align-items: center; justify-content: center; gap: 8px; color: #787774; font-size: 12px; }.guide-loading span { font-size: 18px; animation: guide-spin .8s linear infinite; }.guide-step-bar { display: flex; justify-content: space-between; margin-bottom: 10px; }.guide-step-bar button,.guide-channel-row button,.guide-org-form button,.guide-done > button { min-height: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; padding: 0 11px; border: 1px solid #d3d3d0; border-radius: 6px; background: #fff; color: #37352f; font: inherit; font-size: 11px; font-weight: 600; cursor: pointer; }.guide-step-bar button:hover,.guide-channel-row button:hover { background: #efefed; }.guide-step-bar span { font-size: 15px; }
.guide-channel-list { overflow: hidden; border: 1px solid #e5e3df; border-radius: 8px; }.guide-channel-row { min-height: 82px; display: grid; grid-template-columns: 40px minmax(0,1fr) auto; align-items: center; gap: 14px; padding: 12px 16px; border-bottom: 1px solid #e9e9e7; }.guide-channel-row:last-child { border-bottom: 0; }.guide-channel-row.disabled { background: #fafaf9; color: #9b9a97; }.guide-channel-mark { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 7px; color: #fff; font-size: 13px; font-weight: 700; }.guide-channel-mark.meta { background: #1877f2; }.guide-channel-mark.google { background: #4285f4; }.guide-channel-mark.tiktok { background: #37352f; }.guide-channel-row strong { display: block; font-size: 13px; }.guide-channel-row p { margin: 3px 0 0; color: #787774; font-size: 11px; }.guide-connected { display: inline-flex; align-items: center; gap: 4px; padding: 5px 8px; border-radius: 5px; background: #edf5ee; color: #2f6b3c; font-size: 11px; font-weight: 650; }.guide-connected span { font-size: 14px; }.guide-unavailable { color: #9b9a97; font-size: 11px; }
.guide-org-form { width: min(100%,620px); display: grid; gap: 13px; margin: 4px auto 8px; padding: 18px; border: 1px solid #e5e3df; border-radius: 8px; background: #fafaf9; }.guide-org-form h3 { margin: 0; font-size: 16px; }.guide-org-form p { margin: 4px 0 0; color: #787774; font-size: 11px; }.guide-org-form label { display: grid; gap: 5px; color: #5d5b54; font-size: 11px; font-weight: 600; }.guide-org-form input { height: 36px; padding: 0 10px; border: 1px solid #d3d3d0; border-radius: 6px; outline: 0; background: #fff; color: #37352f; font: inherit; font-size: 12px; }.guide-org-form input:focus { border-color: #2383e2; box-shadow: 0 0 0 3px rgb(35 131 226 / 12%); }.guide-org-form button,.guide-done > button { border-color: #2383e2; background: #2383e2; color: #fff; }.guide-org-form button:disabled,.guide-done > button:disabled,.guide-channel-row button:disabled { cursor: not-allowed; opacity: .55; }
.guide-done { width: min(100%,620px); display: flex; align-items: center; flex-direction: column; margin: 4px auto 8px; text-align: center; }.guide-done-mark { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 8px; background: #edf5ee; color: #2f6b3c; }.guide-done h3 { margin: 12px 0 5px; font-size: 17px; }.guide-done > p { margin: 0; color: #787774; font-size: 11px; }.guide-done dl { width: 100%; display: grid; gap: 7px; margin: 16px 0; }.guide-done dl div { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; border: 1px solid #e5e3df; border-radius: 7px; background: #fafaf9; font-size: 11px; }.guide-done dt { color: #787774; }.guide-done dd { margin: 0; color: #20201e; font-weight: 650; }
.guide-message { margin: 0; padding: 9px 26px; border-top: 1px solid #e9e9e7; background: #f7f7f5; color: #5d5b54; font-size: 11px; }.guide-message.error { background: #fff5f5; color: #a33a3a; }
@keyframes guide-spin { to { transform: rotate(360deg); } }
@media (max-width: 760px) { .guide-backdrop { align-items: start; padding: 10px; }.guide-modal { width: calc(100vw - 20px); max-height: calc(100dvh - 20px); }.guide-head { grid-template-columns: 1fr; padding: 20px 18px; }.guide-progress { width: 100%; }.guide-body { padding: 16px 18px 20px; }.guide-choice-grid { grid-template-columns: 1fr; }.guide-choice { min-height: 190px; }.guide-channel-row { grid-template-columns: 36px minmax(0,1fr); }.guide-channel-row > :last-child { grid-column: 1 / -1; width: 100%; }.guide-connected,.guide-unavailable { justify-content: center; } }
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
