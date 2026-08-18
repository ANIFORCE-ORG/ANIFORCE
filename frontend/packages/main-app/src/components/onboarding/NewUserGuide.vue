<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

type GuidePane = 'intro' | 'connect' | 'done'
type GuideChoice = 'channel' | 'org' | 'skip'
type GuideChannel = 'google' | 'meta' | 'tiktok'

const route = useRoute()
const visible = ref(false)
const pane = ref<GuidePane>('intro')
const choice = ref<GuideChoice>('channel')
const selectedChannel = ref<GuideChannel>('google')
const connectedChannel = ref<GuideChannel | null>(null)
const orgName = ref('')
const inviteCode = ref('')
const doneTitle = ref('初始化已就绪')
const doneCopy = ref('你可以进入 Aniforce 素材工作台查看素材、数据评估和投放状态。未完成项目会保留在引导入口中。')
const toastMessage = ref('')
const orgNameInput = ref<HTMLInputElement | null>(null)
let toastTimer: number | undefined

const GUIDE_COMPLETED_KEY = 'aniforce_new_user_guide_completed'
const GUIDE_DISMISSED_KEY = 'aniforce_new_user_guide_dismissed'
const DEBUG_ENTRY = '?guide=1'

const channelNames: Record<GuideChannel, string> = {
  google: 'Google',
  meta: 'Meta',
  tiktok: 'TikTok',
}

const channelFullNames: Record<GuideChannel, string> = {
  google: 'Google Ads',
  meta: 'Meta Ads',
  tiktok: 'TikTok Ads',
}

const step = computed(() => pane.value === 'intro' ? 1 : 2)
const progressWidth = computed(() => `${step.value * 50}%`)
const summaryChannel = computed(() => connectedChannel.value ? channelFullNames[connectedChannel.value] : '未授权')
const summaryOrg = computed(() => orgName.value.trim() || '未加入')

const showToast = (message: string) => {
  window.clearTimeout(toastTimer)
  toastMessage.value = message
  toastTimer = window.setTimeout(() => {
    toastMessage.value = ''
  }, 2200)
}

const showPane = (nextPane: GuidePane) => {
  pane.value = nextPane
}

const resetGuide = () => {
  pane.value = 'intro'
  choice.value = 'channel'
  selectedChannel.value = 'google'
  connectedChannel.value = null
  orgName.value = ''
  inviteCode.value = ''
  doneTitle.value = '初始化已就绪'
  doneCopy.value = '你可以进入 Aniforce 素材工作台查看素材、数据评估和投放状态。未完成项目会保留在引导入口中。'
}

const openGuide = () => {
  resetGuide()
  visible.value = true
}

const closeGuide = () => {
  visible.value = false
}

const dismissGuide = () => {
  sessionStorage.setItem(GUIDE_DISMISSED_KEY, 'true')
  closeGuide()
}

const selectChoice = async (mode: GuideChoice) => {
  choice.value = mode
  if (mode === 'org') {
    await nextTick()
    orgNameInput.value?.focus()
  }
}

const selectChannel = (channel: GuideChannel) => {
  selectedChannel.value = channel
}

const completeGuide = (kind: 'channel' | 'org') => {
  if (kind === 'org') {
    doneTitle.value = '组织申请已提交'
    doneCopy.value = '系统已记录组织名字和邀请码。管理员通过后，你会共享团队已有的渠道和素材配置。'
  } else {
    doneTitle.value = '渠道授权已完成'
    doneCopy.value = '授权结果已写入工作台状态。后端同步任务会继续读取账户、计划、素材和核心指标。'
  }
  showPane('done')
}

const joinOrganization = () => {
  orgName.value = orgName.value.trim() || 'Aniforce Growth Team'
  inviteCode.value = inviteCode.value.trim() || 'AF-2026-88K'
  completeGuide('org')
  showToast('组织加入申请已提交')
}

const connectChannel = (channel: GuideChannel) => {
  selectChannel(channel)
  connectedChannel.value = channel
  completeGuide('channel')
  showToast(`${channelNames[channel]} 授权已模拟完成`)
}

const restartGuide = () => {
  resetGuide()
}

const finishGuide = () => {
  localStorage.setItem(GUIDE_COMPLETED_KEY, 'true')
  sessionStorage.removeItem(GUIDE_DISMISSED_KEY)
  closeGuide()
}

const handleOpenEvent = () => openGuide()

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && visible.value) dismissGuide()
}

onMounted(() => {
  window.addEventListener('aniforce:open-new-user-guide', handleOpenEvent)
  document.addEventListener('keydown', handleKeydown)

  const debugRequested = route.query.guide === '1'
  const completed = localStorage.getItem(GUIDE_COMPLETED_KEY) === 'true'
  const dismissed = sessionStorage.getItem(GUIDE_DISMISSED_KEY) === 'true'
  if (debugRequested || (!completed && !dismissed)) openGuide()
})

watch(
  () => route.query.guide,
  (guide) => {
    if (guide === '1') openGuide()
  },
)

watch(visible, (isVisible) => {
  document.body.classList.toggle('guide-modal-open', isVisible)
})

onBeforeUnmount(() => {
  window.clearTimeout(toastTimer)
  window.removeEventListener('aniforce:open-new-user-guide', handleOpenEvent)
  document.removeEventListener('keydown', handleKeydown)
  document.body.classList.remove('guide-modal-open')
})

defineExpose({ openGuide, debugEntry: DEBUG_ENTRY })
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      id="firstLoginGuide"
      class="onboard-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guideTitle"
    >
      <section class="onboard-modal">
        <button class="onboard-close" type="button" aria-label="关闭" @click="dismissGuide">×</button>

        <div class="onboard-pane" :class="{ active: pane === 'intro' }" data-guide-pane="intro">
          <header class="onboard-head">
            <div class="onboard-title">
              <div class="onboard-kicker">
                <span class="material-symbols-outlined ico" aria-hidden="true">check</span>
                注册完成后第 1 步
              </div>
              <h2 id="guideTitle">先选择你的初始化方式</h2>
              <p>ANIFORCE 会根据你的选择决定下一步：连接广告渠道、加入已有组织，或暂时进入工作台。</p>
            </div>
            <div class="onboard-progress">
              <strong>Step {{ step }} / 2</strong>
              <div class="onboard-track"><span class="onboard-bar" :style="{ width: progressWidth }" /></div>
            </div>
          </header>

          <div class="onboard-body">
            <div class="onboard-choice-grid">
              <button
                class="onboard-card"
                :class="{ active: choice === 'channel' }"
                type="button"
                data-guide-choice="channel"
                @click="selectChoice('channel')"
              >
                <span class="onboard-icon"><span class="material-symbols-outlined ico" aria-hidden="true">sync_alt</span></span>
                <span class="guide-tag float">推荐</span>
                <h3>渠道配置</h3>
                <p>连接广告渠道后，ANIFORCE 可以读取广告账户、计划、素材和核心指标。</p>
                <span class="guide-tags"><span class="guide-tag">Meta</span><span class="guide-tag">Google</span><span class="guide-tag">TikTok</span></span>
                <span class="onboard-card-foot">
                  <span class="guide-helper">单渠道配置约2min</span>
                  <span class="btn primary guide-card-action" data-guide-next="connect" @click.stop="showPane('connect')">开始配置</span>
                </span>
              </button>

              <button
                class="onboard-card"
                :class="{ active: choice === 'org' }"
                type="button"
                data-guide-choice="org"
                @click="selectChoice('org')"
              >
                <span class="onboard-icon"><span class="material-symbols-outlined ico" aria-hidden="true">group_add</span></span>
                <span class="guide-tag neutral">团队</span>
                <h3>加入组织</h3>
                <p>如果你的团队已经创建工作区，输入组织名字和邀请码即可加入共享配置。</p>
                <span class="guide-tags"><span class="guide-tag">组织名字</span><span class="guide-tag">邀请码</span></span>
                <span class="onboard-card-foot action-only"><span class="btn primary guide-card-action">输入邀请码</span></span>
              </button>

              <button
                class="onboard-card skip-card"
                :class="{ active: choice === 'skip' }"
                type="button"
                data-guide-choice="skip"
                @click="selectChoice('skip')"
              >
                <span class="onboard-icon"><span class="material-symbols-outlined ico" aria-hidden="true">play_arrow</span></span>
                <h3>稍后配置</h3>
                <p>当前还没有组织或渠道账户也没关系，可以先进入工作台熟悉功能。系统会保留配置入口，后续再创建/加入组织并连接广告账户。</p>
                <span class="onboard-card-foot"><span class="btn guide-card-action guide-card-action-muted" @click.stop="dismissGuide">稍后再说</span></span>
              </button>
            </div>

            <div class="onboard-org-form" :class="{ active: choice === 'org' }">
              <label class="field"><span>组织名字</span><input ref="orgNameInput" v-model="orgName" placeholder="例如 Aniforce Growth Team"></label>
              <label class="field"><span>邀请码</span><input v-model="inviteCode" placeholder="例如 AF-2026-88K"></label>
              <button class="btn primary" type="button" @click="joinOrganization"><span class="material-symbols-outlined ico" aria-hidden="true">add</span>申请加入</button>
            </div>
          </div>
        </div>

        <div class="onboard-pane" :class="{ active: pane === 'connect' }" data-guide-pane="connect">
          <div class="guide-channel-page">
            <header class="guide-step-head">
              <div class="guide-step-title">
                <div class="onboard-kicker"><span class="material-symbols-outlined ico" aria-hidden="true">sync_alt</span>Step 2 / 2</div>
                <h2>选择需要连接的广告渠道</h2>
                <p>点击 Connect 后将调用已配置的授权 API，并跳转到对应平台的官方 OAuth 页面。</p>
              </div>
              <div class="guide-step-actions">
                <button class="btn" type="button" @click="showPane('intro')"><span class="material-symbols-outlined ico flip" aria-hidden="true">play_arrow</span>返回</button>
                <button class="btn soft" type="button" @click="dismissGuide">稍后配置</button>
              </div>
            </header>

            <div class="guide-channel-list" role="radiogroup" aria-label="广告渠道">
              <div
                class="guide-channel-row"
                :class="{ active: selectedChannel === 'google' }"
                data-guide-channel="google"
                role="radio"
                :aria-checked="selectedChannel === 'google'"
                tabindex="0"
                @click="selectChannel('google')"
                @keydown.enter.prevent="selectChannel('google')"
                @keydown.space.prevent="selectChannel('google')"
              >
                <span class="guide-radio" />
                <div class="guide-channel-copy">
                  <h3>Connect Google Ads</h3>
                  <p>Authorize Google Ads to let Aniforce read campaigns, customers, assets and metrics.</p>
                </div>
                <button
                  class="guide-connect-btn"
                  :class="{ connected: connectedChannel === 'google' }"
                  type="button"
                  @click.stop="connectChannel('google')"
                >
                  <span v-if="connectedChannel === 'google'" class="material-symbols-outlined ico" aria-hidden="true">check</span>
                  {{ connectedChannel === 'google' ? 'Connected' : 'Connect' }}
                </button>
              </div>

              <div
                class="guide-channel-row"
                :class="{ active: selectedChannel === 'meta' }"
                data-guide-channel="meta"
                role="radio"
                :aria-checked="selectedChannel === 'meta'"
                tabindex="0"
                @click="selectChannel('meta')"
                @keydown.enter.prevent="selectChannel('meta')"
                @keydown.space.prevent="selectChannel('meta')"
              >
                <span class="guide-radio" />
                <div class="guide-channel-copy">
                  <h3>Connect Meta Ads</h3>
                  <p>Authorize Meta Ads to sync ad accounts, campaigns, creatives and delivery data.</p>
                </div>
                <button
                  class="guide-connect-btn"
                  :class="{ connected: connectedChannel === 'meta' }"
                  type="button"
                  @click.stop="connectChannel('meta')"
                >
                  <span v-if="connectedChannel === 'meta'" class="material-symbols-outlined ico" aria-hidden="true">check</span>
                  {{ connectedChannel === 'meta' ? 'Connected' : 'Connect' }}
                </button>
              </div>

              <div
                class="guide-channel-row"
                :class="{ active: selectedChannel === 'tiktok' }"
                data-guide-channel="tiktok"
                role="radio"
                :aria-checked="selectedChannel === 'tiktok'"
                tabindex="0"
                @click="selectChannel('tiktok')"
                @keydown.enter.prevent="selectChannel('tiktok')"
                @keydown.space.prevent="selectChannel('tiktok')"
              >
                <span class="guide-radio" />
                <div class="guide-channel-copy">
                  <h3>Connect TikTok Ads</h3>
                  <p>Authorize TikTok Ads to sync advertisers, Spark assets, campaigns and reports.</p>
                </div>
                <button
                  class="guide-connect-btn"
                  :class="{ connected: connectedChannel === 'tiktok' }"
                  type="button"
                  @click.stop="connectChannel('tiktok')"
                >
                  <span v-if="connectedChannel === 'tiktok'" class="material-symbols-outlined ico" aria-hidden="true">check</span>
                  {{ connectedChannel === 'tiktok' ? 'Connected' : 'Connect' }}
                </button>
              </div>
            </div>

            <footer class="guide-step-foot">
              <span>建议至少完成 1 个渠道授权。授权由后端配置发起，当前页面不展示 App Secret 或账户配置。</span>
              <span class="guide-tag">已选择 {{ channelNames[selectedChannel] }}</span>
            </footer>
          </div>
        </div>

        <div class="onboard-pane" :class="{ active: pane === 'done' }" data-guide-pane="done">
          <header class="onboard-head">
            <div class="onboard-title">
              <div class="onboard-kicker"><span class="material-symbols-outlined ico" aria-hidden="true">check</span>Step 2 / 2</div>
              <h2>完成初始化设置</h2>
              <p>工作台已根据你的选择更新状态。之后仍可从顶部入口重新打开新手引导。</p>
            </div>
            <div class="onboard-progress">
              <strong>Step 2 / 2</strong>
              <div class="onboard-track"><span class="onboard-bar" style="width:100%" /></div>
            </div>
          </header>

          <div class="onboard-body">
            <div class="onboard-done-grid">
              <section class="done-panel">
                <span class="done-mark"><span class="material-symbols-outlined ico" aria-hidden="true">check</span></span>
                <h3>{{ doneTitle }}</h3>
                <p>{{ doneCopy }}</p>
                <div class="guide-summary">
                  <div><span>广告渠道</span><b>{{ summaryChannel }}</b></div>
                  <div><span>组织</span><b>{{ summaryOrg }}</b></div>
                </div>
                <button class="btn primary" type="button" @click="finishGuide">进入 Aniforce 工作台</button>
              </section>

              <section class="done-panel">
                <h3>后续任务</h3>
                <div class="guide-next-list">
                  <div><span class="guide-step-dot"><span class="material-symbols-outlined ico" aria-hidden="true">check</span></span><p><strong>同步广告账户与素材</strong><span>授权完成后自动拉取账户、计划和素材数据。</span></p><b class="guide-tag">{{ connectedChannel ? '已排队' : '待开始' }}</b></div>
                  <div><span class="guide-step-dot"><span class="material-symbols-outlined ico" aria-hidden="true">check</span></span><p><strong>查看素材评估</strong><span>进入当前素材模块，继续筛选素材评分、疲劳度和投放表现。</span></p><b class="guide-tag">可查看</b></div>
                  <div><span class="guide-step-dot"><span class="material-symbols-outlined ico" aria-hidden="true">check</span></span><p><strong>补充团队配置</strong><span>如需共享配置，可从引导入口再次申请加入组织。</span></p><button class="btn soft" type="button" @click="restartGuide">去配置</button></div>
                </div>
                <button class="btn soft" type="button" @click="restartGuide">重新选择初始化方式</button>
              </section>
            </div>
          </div>
        </div>
      </section>

      <div v-if="toastMessage" class="guide-toast" role="status" aria-live="polite">{{ toastMessage }}</div>
    </div>
  </Teleport>
</template>

<style scoped>
:global(body.guide-modal-open) { overflow: hidden; }

.onboard-backdrop {
  --guide-font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  --notion-ink: #37352f;
  --notion-ink-strong: #20201e;
  --notion-muted: #787774;
  --notion-faint: #9b9a97;
  --notion-line: #e9e9e7;
  --notion-line-strong: #d3d3d0;
  --notion-surface: #f7f7f5;
  --notion-surface-hover: #efefed;
  --notion-blue: #2383e2;
  --notion-blue-hover: #1b6fc1;
  --notion-blue-soft: #eaf3fb;
  --notion-green: #2f6b3c;
  --notion-green-soft: #edf5ee;
  --notion-warm: #9f6b53;
  --notion-warm-soft: #f5eeee;
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background: rgba(15, 15, 15, .28);
  color: var(--notion-ink);
  font-family: var(--guide-font-family);
  letter-spacing: 0;
  -webkit-font-smoothing: antialiased;
  backdrop-filter: blur(8px);
}

.onboard-modal button,
.onboard-modal input {
  font-family: var(--guide-font-family);
}

.onboard-modal {
  position: relative;
  width: min(1120px, calc(100vw - 48px));
  max-height: calc(100vh - 48px);
  overflow: auto;
  border: 1px solid var(--notion-line);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 24px 72px rgba(15, 15, 15, .18), 0 2px 8px rgba(15, 15, 15, .06);
}

.onboard-close {
  position: absolute;
  z-index: 4;
  top: 14px;
  right: 14px;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--notion-muted);
  font-size: 18px;
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
}

.onboard-close:hover { background: var(--notion-surface-hover); color: var(--notion-ink); }
.onboard-pane { display: none; }
.onboard-pane.active { display: block; }

.onboard-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px;
  gap: 20px;
  align-items: center;
  padding: 22px 26px;
  border-bottom: 1px solid var(--notion-line);
}

.onboard-kicker {
  min-height: 26px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 8px;
  border-radius: 6px;
  background: var(--notion-blue-soft);
  color: var(--notion-blue);
  font-size: 11px;
  font-weight: 650;
}

.onboard-title h2 { margin: 10px 0 6px; color: var(--notion-ink-strong); font-size: 20px; line-height: 1.2; font-weight: 700; letter-spacing: 0; }
.onboard-title p { margin: 0; color: var(--notion-muted); font-size: 12px; font-weight: 450; line-height: 1.55; }
.onboard-progress { width: 190px; justify-self: end; }
.onboard-progress strong { display: block; margin-bottom: 10px; color: var(--notion-ink); font-size: 12px; font-weight: 650; }
.onboard-track { height: 6px; overflow: hidden; border-radius: 999px; background: var(--notion-surface-hover); }
.onboard-bar { display: block; width: 50%; height: 100%; border-radius: inherit; background: var(--notion-blue); transition: width .2s ease; }
.onboard-body { padding: 20px 26px 24px; }
.onboard-choice-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }

.onboard-card {
  position: relative;
  min-height: 286px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--notion-line);
  border-radius: 8px;
  background: #fff;
  color: var(--notion-ink);
  text-align: left;
  cursor: pointer;
  transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
}

.onboard-card:hover { background: var(--notion-surface); }
.onboard-card.active { border-color: var(--notion-ink); background: #fff; box-shadow: inset 0 0 0 1px var(--notion-ink); }
.onboard-icon { width: 46px; height: 46px; display: grid; place-items: center; border-radius: 8px; background: var(--notion-blue-soft); color: var(--notion-blue); }
.onboard-card:nth-child(2) .onboard-icon { background: var(--notion-warm-soft); color: var(--notion-warm); }
.onboard-card:nth-child(3) .onboard-icon { background: #fbf3db; color: #906b18; }
.onboard-icon .ico { font-size: 24px; }
.onboard-card h3 { margin: 0; font-size: 16px; line-height: 1.25; font-weight: 680; }
.onboard-card p { margin: 0; color: var(--notion-muted); font-size: 12px; font-weight: 450; line-height: 1.6; }
.guide-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.guide-tag { min-height: 22px; display: inline-flex; align-items: center; padding: 0 7px; border: 0; border-radius: 5px; background: var(--notion-surface); color: var(--notion-muted); font-size: 10px; font-weight: 600; }
.guide-tag.float, .guide-tag.neutral { position: absolute; top: 18px; right: 18px; }
.guide-tag.float { background: var(--notion-green-soft); color: var(--notion-green); }
.guide-tag.neutral { background: var(--notion-surface); color: var(--notion-muted); }
.guide-helper { color: var(--notion-faint); font-size: 10.5px; font-weight: 450; line-height: 1.35; }
.onboard-card-foot { min-height: 34px; display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: auto; }
.onboard-card-foot.action-only, .onboard-card.skip-card .onboard-card-foot { justify-content: flex-end; }

.btn {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--notion-line-strong);
  border-radius: 6px;
  background: #fff;
  color: var(--notion-ink);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.btn:hover { background: var(--notion-surface-hover); }
.btn.primary { border-color: var(--notion-blue); background: var(--notion-blue); color: #fff; }
.btn.primary:hover { border-color: var(--notion-blue-hover); background: var(--notion-blue-hover); }
.btn.soft { border-color: var(--notion-line); background: var(--notion-surface); }
.guide-card-action { min-width: 96px; min-height: 34px; padding: 0 12px; }
.guide-card-action-muted { border-color: var(--notion-line); background: var(--notion-surface); color: var(--notion-muted); }

.onboard-org-form { display: none; grid-template-columns: minmax(200px, 1fr) minmax(200px, 1fr) 150px; gap: 10px; align-items: end; margin-top: 14px; padding: 14px; border: 1px solid var(--notion-line); border-radius: 8px; background: var(--notion-surface); }
.onboard-org-form.active { display: grid; }
.field { display: grid; gap: 6px; }
.field span { color: var(--notion-muted); font-size: 11px; font-weight: 600; }
.field input { width: 100%; height: 34px; padding: 0 10px; border: 1px solid var(--notion-line-strong); border-radius: 6px; outline: none; background: #fff; color: var(--notion-ink); font: inherit; font-size: 11px; }
.field input:focus { border-color: var(--notion-blue); box-shadow: 0 0 0 3px rgba(35, 131, 226, .12); }

.guide-channel-page { min-height: 500px; display: grid; grid-template-rows: auto 1fr auto; }
.guide-step-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 20px 26px; border-bottom: 1px solid var(--notion-line); }
.guide-step-title h2 { margin: 7px 0 5px; color: var(--notion-ink-strong); font-size: 17px; line-height: 1.25; font-weight: 700; letter-spacing: 0; }
.guide-step-title p { margin: 0; color: var(--notion-muted); font-size: 11.5px; font-weight: 450; }
.guide-step-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
.guide-channel-list { display: grid; }
.guide-channel-row { min-height: 90px; display: grid; grid-template-columns: 44px minmax(0, 1fr) 112px; gap: 14px; align-items: center; padding: 15px 26px; border-bottom: 1px solid var(--notion-line); background: #fff; cursor: pointer; }
.guide-channel-row:hover { background: var(--notion-surface); }
.guide-channel-row.active { background: #fff; }
.guide-radio { width: 30px; height: 30px; border: 2px solid var(--notion-line-strong); border-radius: 50%; background: #fff; }
.guide-channel-row.active .guide-radio { border-color: var(--notion-blue); background: var(--notion-blue); box-shadow: inset 0 0 0 7px #fff; }
.guide-channel-copy h3 { margin: 0 0 5px; color: var(--notion-ink); font-size: 15px; line-height: 1.25; font-weight: 680; }
.guide-channel-copy p { margin: 0; color: var(--notion-muted); font-size: 11.5px; font-weight: 450; line-height: 1.5; }
.guide-connect-btn { min-height: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid var(--notion-line-strong); border-radius: 6px; background: #fff; color: var(--notion-ink); font-size: 11px; font-weight: 600; cursor: pointer; }
.guide-connect-btn:hover { background: var(--notion-surface-hover); }
.guide-connect-btn.connected { border-color: #cfe4d2; background: var(--notion-green-soft); color: var(--notion-green); }
.guide-step-foot { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 0 26px; border-top: 1px solid var(--notion-line); background: var(--notion-surface); color: var(--notion-muted); font-size: 10.5px; font-weight: 450; }

.onboard-done-grid { display: grid; grid-template-columns: minmax(0, .9fr) minmax(320px, 1fr); gap: 14px; align-items: stretch; }
.done-panel { display: flex; flex-direction: column; padding: 18px; border: 1px solid var(--notion-line); border-radius: 8px; background: #fff; }
.done-panel h3 { margin: 0 0 8px; color: var(--notion-ink-strong); font-size: 17px; line-height: 1.25; font-weight: 700; }
.done-panel p { margin: 0 0 14px; color: var(--notion-muted); font-size: 11.5px; font-weight: 450; line-height: 1.6; }
.done-panel > button { align-self: center; margin-top: auto; }
.done-mark { width: 50px; height: 50px; display: grid; place-items: center; margin-bottom: 14px; border-radius: 8px; background: var(--notion-green-soft); color: var(--notion-green); }
.done-mark .ico { font-size: 28px; }
.guide-summary { display: grid; gap: 8px; margin: 14px 0; }
.guide-summary div { display: flex; justify-content: space-between; gap: 10px; padding: 10px; border: 1px solid var(--notion-line); border-radius: 7px; background: var(--notion-surface); color: var(--notion-muted); font-size: 11px; }
.guide-summary b { color: var(--notion-ink); }
.guide-next-list { display: grid; gap: 8px; margin-bottom: 14px; }
.guide-next-list > div { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 8px; align-items: center; padding: 10px; border: 1px solid var(--notion-line); border-radius: 7px; background: var(--notion-surface); }
.guide-next-list p { margin: 0; }
.guide-next-list strong { display: block; color: var(--notion-ink); font-size: 11px; }
.guide-next-list p span { display: block; margin-top: 2px; color: var(--notion-muted); font-size: 10px; font-weight: 450; }
.guide-step-dot { width: 24px; height: 24px; display: grid; place-items: center; border-radius: 6px; background: var(--notion-green-soft); color: var(--notion-green); }
.guide-step-dot .ico { font-size: 14px; }
.ico { font-size: 18px; line-height: 1; }
.flip { transform: rotate(180deg); }

.guide-toast { position: fixed; z-index: 1002; right: 18px; bottom: 18px; max-width: 360px; padding: 9px 12px; border-radius: 7px; background: var(--notion-ink-strong); color: #fff; box-shadow: 0 10px 30px rgba(15, 15, 15, .2); font-size: 11px; }

@media (max-width: 1020px) {
  .onboard-choice-grid, .onboard-done-grid { grid-template-columns: 1fr; }
  .onboard-card { min-height: 240px; }
  .onboard-org-form { grid-template-columns: 1fr; }
  .guide-channel-row { grid-template-columns: 46px minmax(0, 1fr); }
  .guide-connect-btn { grid-column: 1 / -1; width: 100%; }
}

@media (max-width: 760px) {
  .onboard-backdrop { align-items: flex-start; padding: 10px; }
  .onboard-modal { width: calc(100vw - 20px); max-height: calc(100vh - 20px); }
  .onboard-head { grid-template-columns: 1fr; padding: 22px 18px; }
  .onboard-progress { width: 100%; justify-self: stretch; }
  .onboard-body, .guide-step-head, .guide-channel-row, .guide-step-foot { padding-right: 18px; padding-left: 18px; }
  .guide-step-head, .guide-step-foot { align-items: flex-start; flex-direction: column; }
  .guide-step-actions { justify-content: flex-start; }
  .guide-channel-copy h3 { font-size: 16px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
</style>
