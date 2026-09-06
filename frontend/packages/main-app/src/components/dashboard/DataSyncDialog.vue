<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { cancelMetaAdSetSync, getMetaAdSetSyncProgress, syncMetaAdSetFacts, type MetaAdSetSyncProgress, type MetaAdSetSyncResponse } from '@/api/dashboard'
import '@/styles/settings-notion.css'

interface Account { id: string; name: string; sub_account_id: string; status?: string }
const props = defineProps<{ show: boolean; connectionId: string; accounts: Account[]; currentAccountId?: string }>()
const emit = defineEmits<{ close: []; completed: [result: MetaAdSetSyncResponse] }>()
const searchInput = ref<HTMLInputElement | null>(null)
const search = ref('')
const selected = ref<string[]>([])
const since = ref('')
const until = ref('')
const stage = ref<'form' | 'syncing' | 'result'>('form')
const error = ref('')
const result = ref<MetaAdSetSyncResponse | null>(null)
const progress = ref<MetaAdSetSyncProgress>({ total: 0, completed: 0, succeeded: 0, failed: 0, running: 0, rows_written: 0, percent: 0 })
let activeController: AbortController | null = null
const total = computed(() => selected.value.length)
const runnerPosition = computed(() => `clamp(22px, ${progress.value.percent}%, calc(100% - 22px))`)
const activeAccounts = computed(() => props.accounts.filter(item => item.status === 'active' || !item.status))
const activeAccountIds = computed(() => activeAccounts.value.map(item => item.sub_account_id.replace(/^act_/, '')))
const allSelected = computed(() => activeAccountIds.value.length > 0 && activeAccountIds.value.every(id => selected.value.includes(id)))
const filtered = computed(() => { const q = search.value.trim().toLowerCase(); return activeAccounts.value.filter(item => !q || item.name.toLowerCase().includes(q) || item.sub_account_id.toLowerCase().includes(q)) })
const today = () => new Date().toISOString().slice(0, 10)
const reset = async () => { const end = new Date(); const start = new Date(end); start.setDate(start.getDate() - 29); since.value = start.toISOString().slice(0, 10); until.value = end.toISOString().slice(0, 10); selected.value = activeAccounts.value.map(item => item.sub_account_id.replace(/^act_/, '')); search.value = ''; stage.value = 'form'; error.value = ''; result.value = null; progress.value = { total: 0, completed: 0, succeeded: 0, failed: 0, running: 0, rows_written: 0, percent: 0 }; await nextTick(); searchInput.value?.focus() }
watch(() => props.show, value => { if (value) void reset() })
const toggle = (id: string) => { const index = selected.value.indexOf(id); if (index >= 0) selected.value.splice(index, 1); else selected.value.push(id) }
const selectAll = () => { selected.value = [...activeAccountIds.value] }
const clearAll = () => { selected.value = [] }
const dateError = computed(() => { if (!since.value || !until.value) return '请选择完整时间范围'; const days = (new Date(`${until.value}T00:00:00Z`).getTime() - new Date(`${since.value}T00:00:00Z`).getTime()) / 86400000 + 1; if (days < 1) return '开始日期不能晚于结束日期'; if (days > 31) return '单次同步最多 31 天'; return '' })
const canSubmit = computed(() => selected.value.length > 0 && !dateError.value)
const succeeded = computed(() => result.value?.accounts.filter(item => item.status === 'succeeded') ?? [])
const failed = computed(() => result.value?.accounts.filter(item => item.status === 'failed') ?? [])
const rows = computed(() => succeeded.value.reduce((sum, item) => sum + item.rows_written, 0))
const syncErrorMessage = (cause: unknown) => {
  const response = (cause as { response?: { status?: number; data?: { detail?: unknown } } } | null)?.response
  const detail = response?.data?.detail
  const accountIds = detail && typeof detail === 'object' && Array.isArray((detail as { account_ids?: unknown }).account_ids)
    ? (detail as { account_ids: unknown[] }).account_ids
    : []

  if (response?.status === 409) {
    return accountIds.length
      ? `检测到 ${accountIds.length} 个账号正在同步，请等待当前任务完成后再试。`
      : '所选账号中有账号正在同步，请等待当前任务完成后再试。'
  }

  if (detail && typeof detail === 'object' && (detail as { message?: unknown }).message === 'Accounts are not active bindings') {
    return accountIds.length
      ? `有 ${accountIds.length} 个账号已停用或无同步权限，请刷新账号列表后重试。`
      : '所选账号已停用或无同步权限，请刷新账号列表后重试。'
  }

  return cause instanceof Error && cause.message !== '[object Object]'
    ? cause.message
    : '数据同步失败，请稍后重试。'
}
const run = async () => { if (!canSubmit.value) return; stage.value = 'syncing'; error.value = ''; const request = { connection_id: props.connectionId, account_ids: [...selected.value], since: since.value, until: until.value }; const controller = new AbortController(); activeController = controller; progress.value = { total: selected.value.length, completed: 0, succeeded: 0, failed: 0, running: selected.value.length, rows_written: 0, percent: 0 }; const poll = async () => { try { progress.value = await getMetaAdSetSyncProgress(request) } catch { /* Main sync response owns error reporting. */ } }; const timer = window.setInterval(() => void poll(), 1000); try { result.value = await syncMetaAdSetFacts(request, controller.signal); await poll(); stage.value = 'result' } catch (e) { if (!controller.signal.aborted) error.value = syncErrorMessage(e); stage.value = 'form' } finally { window.clearInterval(timer); if (activeController === controller) activeController = null } }
const cancel = async () => { if (!activeController || stage.value !== 'syncing') return; const controller = activeController; const request = { connection_id: props.connectionId, account_ids: [...selected.value], since: since.value, until: until.value }; try { await cancelMetaAdSetSync(request) } finally { controller.abort(); activeController = null; stage.value = 'form'; error.value = '本次同步已停止，可以重新选择账号后再次同步' } }
const retry = () => { selected.value = failed.value.map(item => item.account_id); result.value = null; stage.value = 'form' }
const finish = () => { if (result.value) emit('completed', result.value); emit('close') }
const close = () => { if (stage.value !== 'syncing') emit('close') }
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="settings-modal-layer data-sync-layer" @click.self="close">
      <section class="settings-modal wide data-sync-modal" role="dialog" aria-modal="true" aria-labelledby="data-sync-title">
        <header class="settings-modal-head"><div><h2 id="data-sync-title">{{ stage === 'result' ? '数据同步结果' : '数据同步' }}</h2><p>{{ stage === 'form' ? '选择要更新的 Meta 广告账号和时间范围' : stage === 'syncing' ? '正在读取 Meta AdSet 日级数据，请保持页面打开' : '已按账号分别记录本次同步结果' }}</p></div><button class="settings-modal-close" type="button" aria-label="关闭" :disabled="stage === 'syncing'" @click="close"><span class="material-symbols-outlined">close</span></button></header>
        <div v-if="stage === 'form'" class="settings-modal-body data-sync-body">
          <section><div class="data-sync-heading"><h3>同步范围</h3><div class="data-sync-selection-actions"><button type="button" :disabled="allSelected" @click="selectAll">全选</button><button type="button" :disabled="!selected.length" @click="clearAll">全部清除</button></div></div><input ref="searchInput" v-model="search" class="sn-search" type="search" placeholder="搜索账号名称或 ID" aria-label="搜索账号" /><div class="data-sync-accounts"><label v-for="account in filtered" :key="account.id" :class="{ selected: selected.includes(account.sub_account_id.replace(/^act_/, '')) }"><input type="checkbox" :checked="selected.includes(account.sub_account_id.replace(/^act_/, ''))" @change="toggle(account.sub_account_id.replace(/^act_/, ''))" /><span><strong>{{ account.name }}</strong><small>{{ account.sub_account_id.replace(/^act_/, '') }}</small></span></label><div v-if="!filtered.length" class="data-sync-empty">没有可同步的 active 账号</div></div></section>
          <section class="data-sync-range"><div class="data-sync-heading"><h3>时间范围</h3><span>默认最近 30 天 · 最多 31 天</span></div><div class="data-sync-dates"><label>开始日期<input v-model="since" class="sn-input" type="date" /></label><label>结束日期<input v-model="until" class="sn-input" type="date" :max="today()" /></label></div><p v-if="dateError" class="sn-error">{{ dateError }}</p></section>
          <div class="data-sync-summary"><span class="material-symbols-outlined">info</span><p><strong>{{ total }} 个广告账号</strong> · {{ since }} 至 {{ until }} · 固定同步 <strong>AdSet 日级数据</strong></p></div><p v-if="error" class="sn-error" role="alert">{{ error }}</p>
        </div>
        <div v-else-if="stage === 'syncing'" class="settings-modal-body data-sync-progress" aria-live="polite">
          <div class="data-sync-progress-summary">
            <span class="material-symbols-outlined data-sync-spinner">progress_activity</span>
            <h3>已完成 {{ progress.completed }} / {{ progress.total }} 个广告账号</h3>
            <div class="data-sync-progress-track" role="progressbar" aria-label="数据同步进度" :aria-valuenow="progress.percent" aria-valuemin="0" aria-valuemax="100">
              <span class="data-sync-progress-rail"><i class="data-sync-progress-fill" :style="{ width: `${progress.percent}%` }"></i><i class="data-sync-checkpoint checkpoint-one"></i><i class="data-sync-checkpoint checkpoint-two"></i><i class="data-sync-checkpoint checkpoint-three"></i></span>
              <span class="data-sync-runner" :style="{ left: runnerPosition }" aria-hidden="true">
                <svg class="data-sync-runner-figure" viewBox="0 0 48 32" shape-rendering="crispEdges">
                  <g class="pixel-fill">
                    <path d="M1 9H4V11H8V13H12V15H15V11H18V8H22V5H26V2H40V4H44V12H35V14H41V17H32V19H28V21H15V19H11V17H7V15H3V13H1V9Z"></path>
                    <path d="M25 14H29V16H33V18H29V17H25V14Z"></path>
                  </g>
                  <rect class="pixel-eye" x="38" y="5" width="2" height="2"></rect>
                  <rect class="pixel-cutout" x="37" y="11" width="7" height="2"></rect>
                  <g class="pixel-fill runner-frame runner-frame-one">
                    <path d="M15 20H21V26H18V30H12V27H15V20Z"></path>
                    <path d="M23 20H29V25H35V28H27V26H23V20Z"></path>
                  </g>
                  <g class="pixel-fill runner-frame runner-frame-two">
                    <path d="M15 20H21V25H27V28H19V26H15V20Z"></path>
                    <path d="M23 20H29V27H32V30H26V27H23V20Z"></path>
                  </g>
                </svg>
              </span>
            </div>
            <strong class="data-sync-progress-value">{{ progress.percent.toFixed(0) }}%</strong>
            <p>成功 {{ progress.succeeded }} 个 · 失败 {{ progress.failed }} 个 · 已写入 {{ progress.rows_written }} 条 AdSet 日级事实</p>
            <small>Meta 数据按 AdSet × 日期返回；后端正在按账号分页处理，请保持页面打开。</small>
          </div>

          <div class="data-sync-journey" aria-hidden="true">
            <span class="data-sync-orbit orbit-one"></span>
            <span class="data-sync-orbit orbit-two"></span>
            <div class="data-sync-node source">
              <span class="data-sync-node-icon material-symbols-outlined">campaign</span>
              <span><strong>Meta Ads</strong><small>读取账号数据</small></span>
              <i></i>
            </div>
            <div class="data-sync-lane">
              <span class="data-sync-lane-label">解析 · 校验 · 写入</span>
              <span class="data-sync-route"></span>
              <i class="data-sync-packet packet-one"><span class="material-symbols-outlined">calendar_month</span></i>
              <i class="data-sync-packet packet-two"><span class="material-symbols-outlined">account_tree</span></i>
              <i class="data-sync-packet packet-three"><span class="material-symbols-outlined">table_rows</span></i>
              <i class="data-sync-packet packet-four"><span class="material-symbols-outlined">monitoring</span></i>
            </div>
            <div class="data-sync-node target">
              <span class="data-sync-node-icon material-symbols-outlined">database</span>
              <span><strong>AdSet 数据集</strong><small>{{ progress.rows_written }} 条已就绪</small></span>
              <i></i>
            </div>
            <div class="data-sync-pipeline-status">
              <span><i></i>账号分页</span>
              <span><i></i>AdSet × 日期</span>
              <span><i></i>实时写入</span>
            </div>
          </div>
        </div>
        <div v-else class="settings-modal-body data-sync-result-body" aria-live="polite">
          <div class="data-sync-result" :class="{ partial: failed.length }">
            <span class="material-symbols-outlined">{{ failed.length ? 'warning' : 'check_circle' }}</span>
            <div><strong>{{ failed.length ? '部分完成' : '同步完成' }}</strong><p>成功 {{ succeeded.length }} 个，失败 {{ failed.length }} 个，写入 {{ rows }} 条日级事实</p></div>
          </div>
          <div class="data-sync-result-list">
            <div v-for="item in result?.accounts" :key="item.account_id">
              <span class="material-symbols-outlined">{{ item.status === 'succeeded' ? 'check_circle' : 'error' }}</span>
              <span><strong>{{ item.account_name || item.account_id }}</strong><small>{{ item.account_id }}</small></span>
              <em>{{ item.status === 'succeeded' ? `${item.rows_written} 条` : item.message || '同步失败' }}</em>
            </div>
          </div>
          <div v-if="!failed.length" class="data-sync-success-scene">
            <div class="data-sync-success-visual" aria-hidden="true">
              <span class="data-sync-success-card"><i></i><i></i><i></i></span>
              <span class="data-sync-success-route">
                <i class="success-packet packet-a"></i>
                <i class="success-packet packet-b"></i>
              </span>
              <span class="data-sync-success-mark">
                <svg viewBox="0 0 52 52">
                  <circle cx="26" cy="26" r="20"></circle>
                  <path d="M17 26.5 23 32l12-13"></path>
                </svg>
              </span>
              <i class="success-spark spark-a"></i>
              <i class="success-spark spark-b"></i>
              <i class="success-spark spark-c"></i>
            </div>
            <strong>本次数据已同步</strong>
            <small>{{ rows }} 条 AdSet 日级事实已写入数据概览</small>
          </div>
        </div>
        <footer class="settings-modal-actions" :class="{ 'data-sync-actions-running': stage === 'syncing' }"><template v-if="stage === 'form'"><button class="sn-button" type="button" @click="close">取消</button><button class="sn-button primary" type="button" :disabled="!canSubmit" @click="run"><span class="material-symbols-outlined">cloud_sync</span>开始同步</button></template><template v-else-if="stage === 'result'"><button v-if="failed.length" class="sn-button" type="button" @click="retry">重试失败账号</button><button class="sn-button primary" type="button" @click="finish">查看更新数据</button></template><template v-else><button class="sn-button danger data-sync-stop" type="button" @click="cancel">停止同步</button><small class="data-sync-running">可以安全停止，已完成账户不会丢失</small></template></footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.data-sync-modal {
  height: min(680px, calc(100dvh - 40px));
  min-height: 0;
}

.settings-modal-head p {
  margin: 4px 0 0;
  color: var(--sn-steel);
  font-size: 10px;
}

.data-sync-body {
  display: grid;
  gap: 18px;
}

.data-sync-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.data-sync-heading h3 {
  margin: 0;
  color: var(--sn-ink);
  font-size: 12px;
}

.data-sync-heading span {
  color: var(--sn-stone);
  font-size: 9px;
}

.data-sync-selection-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.data-sync-selection-actions button {
  min-height: 26px;
  padding: 4px 10px;
  border: 1px solid var(--sn-line);
  border-radius: 6px;
  background: #fff;
  color: var(--sn-slate);
  font: inherit;
  font-size: 9px;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease, color .15s ease;
}

.data-sync-selection-actions button:hover:not(:disabled) {
  border-color: var(--sn-line-strong);
  background: var(--sn-surface-soft);
  color: var(--sn-ink);
}

.data-sync-selection-actions button:disabled {
  color: var(--sn-stone);
  cursor: not-allowed;
  opacity: .58;
}

.data-sync-accounts {
  max-height: 260px;
  overflow: auto;
  border: 1px solid var(--sn-line);
  border-radius: 8px;
  margin-top: 8px;
}

.data-sync-accounts label {
  min-height: 50px;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 7px 11px;
  border-bottom: 1px solid var(--sn-line-soft);
  cursor: pointer;
}

.data-sync-accounts label:last-of-type { border-bottom: 0; }
.data-sync-accounts label.selected { background: var(--sn-surface-soft); }
.data-sync-accounts label.disabled { opacity: .45; cursor: not-allowed; }
.data-sync-accounts strong,
.data-sync-accounts small { display: block; }
.data-sync-accounts strong { color: var(--sn-charcoal); font-size: 11px; }
.data-sync-accounts small { margin-top: 3px; color: var(--sn-stone); font-size: 9px; }
.data-sync-empty { padding: 28px; color: var(--sn-stone); font-size: 10px; text-align: center; }
.data-sync-range { padding-top: 17px; border-top: 1px solid var(--sn-line-soft); }
.data-sync-dates { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.data-sync-dates label { display: grid; gap: 6px; color: var(--sn-slate); font-size: 10px; }
.data-sync-dates input { margin-top: 0; }

.data-sync-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 7px;
  background: var(--sn-surface-soft);
  color: var(--sn-slate);
}

.data-sync-summary p { margin: 0; font-size: 10px; }
.data-sync-summary .material-symbols-outlined { font-size: 17px; }

.data-sync-progress {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 26px 42px 22px;
  overflow: hidden;
  text-align: center;
}

.data-sync-progress-summary {
  width: 100%;
  display: grid;
  place-items: center;
}

.data-sync-spinner {
  color: var(--sn-blue);
  font-size: 30px;
  animation: data-sync-spin .8s linear infinite;
}

.data-sync-progress h3 {
  margin: 10px 0 0;
  color: var(--sn-ink);
  font-size: 13px;
}

.data-sync-progress-track {
  position: relative;
  width: min(680px, 100%);
  height: 38px;
  margin: 12px 0 2px;
}

.data-sync-progress-rail {
  position: absolute;
  right: 0;
  bottom: 5px;
  left: 0;
  height: 8px;
  border: 1px solid #e2e0dc;
  border-radius: 99px;
  background: #eeece9;
  overflow: hidden;
}

.data-sync-progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2383e2, #4a9bea);
  transition: width .35s ease;
}

.data-sync-checkpoint {
  position: absolute;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .92);
  box-shadow: 0 0 0 1px rgba(55, 53, 47, .08);
  transform: translate(-50%, -50%);
}

.checkpoint-one { left: 25%; }
.checkpoint-two { left: 50%; }
.checkpoint-three { left: 75%; }

.data-sync-runner {
  position: absolute;
  bottom: 5px;
  z-index: 2;
  width: 48px;
  height: 32px;
  color: var(--sn-charcoal);
  transform: translateX(-50%);
  transition: left .45s cubic-bezier(.22, .8, .36, 1);
}

.data-sync-runner-figure {
  width: 48px;
  height: 32px;
  overflow: visible;
  animation: data-sync-pixel-bob .52s steps(2, end) infinite;
}

.data-sync-runner-figure .pixel-fill { fill: currentColor; }
.data-sync-runner-figure .pixel-eye,
.data-sync-runner-figure .pixel-cutout { fill: #fff; }
.runner-frame-one { animation: data-sync-pixel-frame-one .52s steps(1, end) infinite; }
.runner-frame-two { opacity: 0; animation: data-sync-pixel-frame-two .52s steps(1, end) infinite; }

.data-sync-progress-value { color: var(--sn-blue); font-size: 11px; }
.data-sync-progress p { max-width: 420px; margin: 8px 0 0; color: var(--sn-slate); font-size: 10px; line-height: 1.5; }
.data-sync-progress small { max-width: 420px; margin-top: 4px; color: var(--sn-stone); font-size: 9px; line-height: 1.5; }

.data-sync-journey {
  position: relative;
  isolation: isolate;
  width: min(680px, 100%);
  min-height: 205px;
  flex: 1;
  display: grid;
  grid-template-columns: 150px minmax(150px, 1fr) 150px;
  align-items: center;
  gap: 22px;
  margin-top: 20px;
  padding: 26px 24px 46px;
  border: 1px solid #e4e8f1;
  border-radius: 14px;
  background:
    radial-gradient(circle at 12% 22%, rgba(255, 121, 89, .10), transparent 30%),
    radial-gradient(circle at 88% 72%, rgba(45, 129, 247, .11), transparent 32%),
    linear-gradient(145deg, #fdfdfd 0%, #f7f9fd 52%, #fbfaf8 100%);
  overflow: hidden;
}

.data-sync-orbit {
  position: absolute;
  z-index: -1;
  width: 110px;
  height: 110px;
  border: 1px solid rgba(45, 129, 247, .12);
  border-radius: 50%;
  animation: data-sync-float 5s ease-in-out infinite;
}

.orbit-one { top: -58px; left: 28%; }
.orbit-two { right: 24%; bottom: -72px; width: 138px; height: 138px; animation-delay: -2.4s; }

.data-sync-node {
  position: relative;
  z-index: 2;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px;
  border: 1px solid rgba(55, 53, 47, .10);
  border-radius: 12px;
  background: rgba(255, 255, 255, .92);
  box-shadow: 0 10px 28px rgba(31, 42, 68, .08);
  text-align: left;
}

.data-sync-node-icon {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  font-size: 20px;
}

.data-sync-node.source .data-sync-node-icon { background: #fff0eb; color: #e35b36; }
.data-sync-node.target .data-sync-node-icon { background: #eaf3ff; color: var(--sn-blue); }
.data-sync-node span { min-width: 0; }
.data-sync-node strong,
.data-sync-node small { display: block; white-space: nowrap; }
.data-sync-node strong { overflow: hidden; color: var(--sn-charcoal); font-size: 10px; text-overflow: ellipsis; }
.data-sync-node small { margin-top: 3px; color: var(--sn-stone); font-size: 8px; }

.data-sync-node > i {
  position: absolute;
  inset: -5px;
  z-index: -1;
  border: 1px solid rgba(45, 129, 247, .15);
  border-radius: 15px;
  animation: data-sync-pulse 2.2s ease-out infinite;
}

.data-sync-node.source > i { border-color: rgba(227, 91, 54, .18); animation-delay: -1.1s; }

.data-sync-lane {
  position: relative;
  height: 90px;
}

.data-sync-lane-label {
  position: absolute;
  top: 4px;
  left: 50%;
  color: var(--sn-steel);
  font-size: 8px;
  white-space: nowrap;
  transform: translateX(-50%);
}

.data-sync-route {
  position: absolute;
  top: 47px;
  left: 0;
  width: 100%;
  height: 2px;
  background: repeating-linear-gradient(90deg, #c8d5e8 0 5px, transparent 5px 10px);
}

.data-sync-route::after {
  position: absolute;
  inset: -2px 0;
  content: '';
  background: linear-gradient(90deg, transparent, rgba(45, 129, 247, .45), transparent);
  filter: blur(2px);
  animation: data-sync-flow 2.4s linear infinite;
}

.data-sync-packet {
  position: absolute;
  top: 48px;
  left: 0;
  z-index: 3;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border: 1px solid #dfe6f1;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 5px 14px rgba(31, 42, 68, .12);
  color: var(--sn-blue);
  opacity: 0;
  transform: translate(-50%, -50%);
  animation: data-sync-travel 4s ease-in-out infinite;
}

.data-sync-packet .material-symbols-outlined { font-size: 14px; }
.packet-two { color: #835bd8; animation-delay: -1s; }
.packet-three { color: #e66c45; animation-delay: -2s; }
.packet-four { color: #279a72; animation-delay: -3s; }

.data-sync-pipeline-status {
  position: absolute;
  right: 18px;
  bottom: 14px;
  left: 18px;
  display: flex;
  justify-content: center;
  gap: 18px;
}

.data-sync-pipeline-status span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--sn-steel);
  font-size: 8px;
}

.data-sync-pipeline-status i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #4eaa83;
  box-shadow: 0 0 0 3px rgba(78, 170, 131, .10);
  animation: data-sync-status 1.8s ease-in-out infinite;
}

.data-sync-pipeline-status span:nth-child(2) i { animation-delay: -.6s; }
.data-sync-pipeline-status span:nth-child(3) i { animation-delay: -1.2s; }

.data-sync-result {
  display: flex;
  gap: 10px;
  padding: 13px;
  border-radius: 8px;
  background: var(--sn-success-bg);
  color: var(--sn-success);
}

.data-sync-result.partial { background: var(--sn-warning-bg); color: var(--sn-warning); }
.data-sync-result strong { font-size: 12px; }
.data-sync-result p { margin: 4px 0 0; color: var(--sn-slate); font-size: 10px; }
.data-sync-result-body { min-height: 0; flex: 1; display: flex; flex-direction: column; gap: 18px; }
.data-sync-result-list { border: 1px solid var(--sn-line); border-radius: 8px; overflow: hidden; }
.data-sync-result-list > div { min-height: 52px; display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; align-items: center; gap: 9px; padding: 8px 11px; border-bottom: 1px solid var(--sn-line-soft); }
.data-sync-result-list > div:last-child { border-bottom: 0; }
.data-sync-result-list .material-symbols-outlined { color: var(--sn-success); font-size: 18px; }
.data-sync-result-list strong,
.data-sync-result-list small { display: block; }
.data-sync-result-list strong { color: var(--sn-charcoal); font-size: 10px; }
.data-sync-result-list small { margin-top: 2px; color: var(--sn-stone); font-size: 8px; }
.data-sync-result-list em { color: var(--sn-steel); font-size: 9px; font-style: normal; }

.data-sync-success-scene {
  position: relative;
  min-height: 170px;
  flex: 1;
  display: grid;
  place-content: center;
  justify-items: center;
  padding: 24px;
  border: 1px solid var(--sn-line-soft);
  border-radius: 12px;
  background:
    radial-gradient(circle at 1px 1px, rgba(55, 53, 47, .055) 1px, transparent 0) 0 0 / 16px 16px,
    linear-gradient(180deg, #fff 0%, #fafcf9 100%);
  overflow: hidden;
  text-align: center;
}

.data-sync-success-scene > strong {
  margin-top: 8px;
  color: var(--sn-charcoal);
  font-size: 11px;
  font-weight: 600;
}

.data-sync-success-scene > small {
  margin-top: 4px;
  color: var(--sn-stone);
  font-size: 9px;
}

.data-sync-success-visual {
  position: relative;
  width: min(270px, 70vw);
  height: 92px;
}

.data-sync-success-card {
  position: absolute;
  top: 18px;
  left: 10px;
  width: 70px;
  height: 54px;
  display: grid;
  align-content: center;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--sn-line);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(55, 53, 47, .06);
  animation: data-sync-success-card-in .45s cubic-bezier(.2, .8, .3, 1) both;
}

.data-sync-success-card::before {
  position: absolute;
  top: 7px;
  left: 8px;
  width: 5px;
  height: 5px;
  border-radius: 2px;
  background: #57a37b;
  content: '';
}

.data-sync-success-card i {
  height: 3px;
  border-radius: 2px;
  background: #dedcd7;
}

.data-sync-success-card i:nth-child(1) { width: 100%; }
.data-sync-success-card i:nth-child(2) { width: 72%; }
.data-sync-success-card i:nth-child(3) { width: 86%; }

.data-sync-success-route {
  position: absolute;
  top: 45px;
  right: 56px;
  left: 78px;
  height: 2px;
  background: repeating-linear-gradient(90deg, #cad7ce 0 5px, transparent 5px 10px);
}

.success-packet {
  position: absolute;
  top: 50%;
  left: 0;
  width: 8px;
  height: 8px;
  border: 2px solid #fff;
  border-radius: 2px;
  background: #57a37b;
  box-shadow: 0 0 0 1px rgba(49, 120, 75, .22);
  opacity: 0;
  transform: translate(-50%, -50%);
  animation: data-sync-success-packet 2.8s ease-in-out infinite;
}

.success-packet.packet-b { animation-delay: -1.4s; }

.data-sync-success-mark {
  position: absolute;
  top: 12px;
  right: 4px;
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #edf7f0;
  box-shadow: 0 0 0 8px rgba(87, 163, 123, .08);
  animation: data-sync-success-mark-in .55s .45s cubic-bezier(.2, .9, .3, 1.25) both;
}

.data-sync-success-mark svg { width: 52px; height: 52px; overflow: visible; }
.data-sync-success-mark circle,
.data-sync-success-mark path { fill: none; stroke: #31784b; stroke-linecap: round; stroke-linejoin: round; }
.data-sync-success-mark circle { stroke-width: 2; stroke-dasharray: 126; stroke-dashoffset: 126; animation: data-sync-success-ring .7s .55s ease-out forwards; }
.data-sync-success-mark path { stroke-width: 2.6; stroke-dasharray: 24; stroke-dashoffset: 24; animation: data-sync-success-check .35s 1.1s ease-out forwards; }

.success-spark {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 2px;
  background: #8abb9d;
  opacity: .35;
  animation: data-sync-success-spark 2.4s ease-in-out infinite;
}

.success-spark.spark-a { top: 6px; right: 82px; }
.success-spark.spark-b { right: 78px; bottom: 8px; width: 4px; height: 4px; animation-delay: -.8s; }
.success-spark.spark-c { top: 10px; left: 92px; width: 4px; height: 4px; animation-delay: -1.6s; }

.data-sync-actions-running {
  min-height: 78px;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 6px;
  padding-top: 10px;
  padding-bottom: 10px;
}

.data-sync-stop {
  width: 100%;
  min-height: 36px;
  justify-content: center;
}

.data-sync-running {
  margin: 0;
  color: var(--sn-steel);
  font-size: 9px;
  line-height: 1.4;
  text-align: center;
}

@keyframes data-sync-spin {
  to { transform: rotate(360deg); }
}

@keyframes data-sync-pixel-bob {
  0%, 49% { transform: translateY(0); }
  50%, 100% { transform: translateY(-1px); }
}

@keyframes data-sync-pixel-frame-one {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

@keyframes data-sync-pixel-frame-two {
  0%, 49% { opacity: 0; }
  50%, 100% { opacity: 1; }
}

@keyframes data-sync-travel {
  0% { left: 0; opacity: 0; transform: translate(-50%, -50%) scale(.7); }
  10% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  82% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  95%, 100% { left: 100%; opacity: 0; transform: translate(-50%, -50%) scale(.7); }
}

@keyframes data-sync-flow {
  from { transform: translateX(-100%); }
  to { transform: translateX(100%); }
}

@keyframes data-sync-pulse {
  0% { opacity: .8; transform: scale(.96); }
  75%, 100% { opacity: 0; transform: scale(1.08); }
}

@keyframes data-sync-status {
  0%, 100% { opacity: .45; transform: scale(.8); }
  50% { opacity: 1; transform: scale(1.15); }
}

@keyframes data-sync-float {
  0%, 100% { transform: translateY(0) rotate(0); }
  50% { transform: translateY(9px) rotate(8deg); }
}

@keyframes data-sync-success-card-in {
  from { opacity: 0; transform: translateX(-10px) scale(.96); }
  to { opacity: 1; transform: translateX(0) scale(1); }
}

@keyframes data-sync-success-packet {
  0% { left: 0; opacity: 0; transform: translate(-50%, -50%) scale(.7); }
  14% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  78% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  92%, 100% { left: 100%; opacity: 0; transform: translate(-50%, -50%) scale(.7); }
}

@keyframes data-sync-success-mark-in {
  from { opacity: 0; transform: scale(.72); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes data-sync-success-ring { to { stroke-dashoffset: 0; } }
@keyframes data-sync-success-check { to { stroke-dashoffset: 0; } }

@keyframes data-sync-success-spark {
  0%, 100% { opacity: .22; transform: translateY(2px) rotate(0); }
  50% { opacity: .7; transform: translateY(-3px) rotate(45deg); }
}

@media (max-width: 620px) {
  .data-sync-progress { padding-right: 20px; padding-left: 20px; }
  .data-sync-journey { grid-template-columns: 112px minmax(90px, 1fr) 112px; gap: 10px; padding-right: 14px; padding-left: 14px; }
  .data-sync-node { gap: 7px; padding: 9px; }
  .data-sync-node-icon { width: 30px; height: 30px; flex-basis: 30px; font-size: 17px; }
}

@media (max-width: 520px) {
  .data-sync-modal { height: calc(100dvh - 20px); }
  .data-sync-dates { grid-template-columns: 1fr; }
  .data-sync-progress { padding: 18px 14px; }
  .data-sync-journey { min-height: 180px; grid-template-columns: 78px minmax(70px, 1fr) 78px; margin-top: 14px; }
  .data-sync-node { display: grid; justify-items: center; gap: 5px; text-align: center; }
  .data-sync-node small { display: none; }
  .data-sync-pipeline-status { gap: 10px; }
}

@media (prefers-reduced-motion: reduce) {
  .data-sync-spinner,
  .data-sync-runner-figure,
  .runner-frame,
  .data-sync-orbit,
  .data-sync-node > i,
  .data-sync-route::after,
  .data-sync-pipeline-status i,
  .data-sync-success-card,
  .data-sync-success-mark,
  .data-sync-success-mark circle,
  .data-sync-success-mark path,
  .success-spark { animation: none; }
  .data-sync-packet { animation: none; opacity: 1; }
  .success-packet { animation: none; opacity: 1; }
  .success-packet.packet-a { left: 38%; }
  .success-packet.packet-b { left: 72%; }
  .packet-one { left: 12%; }
  .packet-two { left: 38%; }
  .packet-three { left: 64%; }
  .packet-four { left: 90%; }
  .data-sync-success-mark circle,
  .data-sync-success-mark path { stroke-dashoffset: 0; }
  .runner-frame-one { opacity: 1; }
  .runner-frame-two { opacity: 0; }
}
</style>
