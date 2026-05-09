<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const status = computed(() => String(route.query.status || ''))
const message = computed(() => String(route.query.message || ''))
const count = computed(() => Number(route.query.count || 0))

onMounted(() => {
  const query: Record<string, string> = { status: status.value || 'error' }
  if (message.value) query.message = message.value
  if (count.value) query.count = String(count.value)
  window.setTimeout(() => router.replace({ path: '/platform-accounts/manage', query }), status.value === 'success' ? 800 : 1400)
})
</script>

<template>
  <main class="min-h-screen bg-slate-50 flex items-center justify-center px-6">
    <section class="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div v-if="status === 'success'" class="space-y-3">
        <div class="h-10 w-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
          <span class="material-symbols-outlined">check_circle</span>
        </div>
        <h1 class="text-xl font-bold text-slate-900">Meta Business 已连接</h1>
        <p class="text-sm text-slate-600">已同步 {{ count }} 个广告账户，正在返回账户操作页。</p>
      </div>

      <div v-else class="space-y-3">
        <div class="h-10 w-10 rounded-full bg-red-50 text-red-600 flex items-center justify-center">
          <span class="material-symbols-outlined">error</span>
        </div>
        <h1 class="text-xl font-bold text-slate-900">Meta 授权失败</h1>
        <p class="text-sm text-slate-600">{{ message || '授权流程未完成，请重新连接 Meta Business。' }}</p>
        <button class="mt-2 px-4 py-2 rounded-md bg-primary text-white text-sm" @click="router.replace({ path: '/platform-accounts/manage', query: { status: 'error', message } })">
          返回广告账户
        </button>
      </div>
    </section>
  </main>
</template>
