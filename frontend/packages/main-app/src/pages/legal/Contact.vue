<script setup lang="ts">
import { computed, ref } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const form = ref({
  name: '',
  company: '',
  role: '',
  email: '',
  phone: '',
  need: '',
})

const submitted = ref(false)

const isReady = computed(() =>
  form.value.name.trim()
  && form.value.company.trim()
  && form.value.email.trim()
  && form.value.need.trim(),
)

function handleSubmit() {
  if (!isReady.value) return
  submitted.value = true
}

const copy = {
  cn: {
    eyebrow: '马上体验',
    titleLines: ['请留下相关信息，', '我们的产品专家将为您升级AI广告工作流'],
    fields: {
      name: '姓名',
      namePlaceholder: '你的姓名',
      company: '公司',
      companyPlaceholder: '公司名称',
      role: '职位',
      rolePlaceholder: '增长 / 投放 / 运营',
      email: '邮箱',
      emailPlaceholder: 'name@company.com',
      phone: '手机号',
      phonePlaceholder: '用于后续联系',
      need: '主要需求',
      needPlaceholder: '例如：素材生成 / 广告盯盘 / 投放复盘',
    },
    submit: '提交体验申请',
    success: '已收到你的信息，我们会尽快联系你。',
    companyInfo: {
      eyebrow: '公司信息',
      title: 'ANIFORCE 品牌归属',
      ownership: 'ANIFORCE 是由 aniforce 拥有并运营的产品和品牌。',
      legalName: '法定注册公司名称：aniforce',
      website: '官网：https://www.aniforce.cc',
      email: '联系邮箱：support@aniforce.cc',
      apiNote: '业务、产品、隐私或 Google Ads API 相关问题，请通过 support@aniforce.cc 联系我们。',
    },
  },
  en: {
    eyebrow: 'Start now',
    titleLines: ['Try for Free,', 'upgrade your AI advertising workflow'],
    fields: {
      name: 'Name',
      namePlaceholder: 'Your name',
      company: 'Company',
      companyPlaceholder: 'Company name',
      role: 'Role',
      rolePlaceholder: 'Growth / Media Buying / Operations',
      email: 'Email',
      emailPlaceholder: 'name@company.com',
      phone: 'Phone',
      phonePlaceholder: 'For follow-up contact',
      need: 'Primary need',
      needPlaceholder: 'Creative generation / ad monitoring / campaign review',
    },
    submit: 'Submit request',
    success: 'We have received your information and will contact you soon.',
    companyInfo: {
      eyebrow: 'Company Information',
      title: 'ANIFORCE Brand Ownership',
      ownership: 'ANIFORCE is a product and brand owned and operated by aniforce.',
      legalName: 'Legal Company Name: aniforce',
      website: 'Website: https://www.aniforce.cc',
      email: 'Contact Email: support@aniforce.cc',
      apiNote: 'For business, product, privacy, or Google Ads API related inquiries, please contact support@aniforce.cc.',
    },
  },
}

const pageCopy = computed(() => copy[language.value])
</script>

<template>
  <main class="px-6 py-16 lg:px-10">
    <div class="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[0.9fr_1.1fr]">
      <section>
        <p class="text-sm font-semibold uppercase tracking-[0.24em] text-primary">{{ pageCopy.eyebrow }}</p>
        <h1 class="mt-4 text-3xl font-black leading-snug md:text-4xl">
          <span v-for="line in pageCopy.titleLines" :key="line" class="block">{{ line }}</span>
        </h1>
        <div class="mt-8 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{{ pageCopy.companyInfo.eyebrow }}</p>
          <h2 class="mt-3 text-xl font-bold text-slate-950">{{ pageCopy.companyInfo.title }}</h2>
          <p class="mt-3 text-sm leading-7 text-slate-600">{{ pageCopy.companyInfo.ownership }}</p>
          <dl class="mt-4 space-y-2 text-sm text-slate-700">
            <div>{{ pageCopy.companyInfo.legalName }}</div>
            <div>{{ pageCopy.companyInfo.website }}</div>
            <div>
              {{ pageCopy.companyInfo.email }}
            </div>
          </dl>
          <p class="mt-4 text-sm leading-7 text-slate-600">{{ pageCopy.companyInfo.apiNote }}</p>
        </div>
      </section>

      <section class="rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <form class="grid gap-4" @submit.prevent="handleSubmit">
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700">{{ pageCopy.fields.name }}</label>
              <input v-model="form.name" class="w-full rounded-md border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" type="text" :placeholder="pageCopy.fields.namePlaceholder" />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700">{{ pageCopy.fields.company }}</label>
              <input v-model="form.company" class="w-full rounded-md border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" type="text" :placeholder="pageCopy.fields.companyPlaceholder" />
            </div>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700">{{ pageCopy.fields.role }}</label>
              <input v-model="form.role" class="w-full rounded-md border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" type="text" :placeholder="pageCopy.fields.rolePlaceholder" />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700">{{ pageCopy.fields.email }}</label>
              <input v-model="form.email" class="w-full rounded-md border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" type="email" :placeholder="pageCopy.fields.emailPlaceholder" />
            </div>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700">{{ pageCopy.fields.phone }}</label>
              <input v-model="form.phone" class="w-full rounded-md border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" type="tel" :placeholder="pageCopy.fields.phonePlaceholder" />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700">{{ pageCopy.fields.need }}</label>
              <input v-model="form.need" class="w-full rounded-md border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" type="text" :placeholder="pageCopy.fields.needPlaceholder" />
            </div>
          </div>

          <button
            type="submit"
            class="mt-2 rounded-md bg-primary px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            :disabled="!isReady"
          >
            {{ pageCopy.submit }}
          </button>

          <p v-if="submitted" class="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {{ pageCopy.success }}
          </p>
        </form>
      </section>
    </div>
  </main>
</template>
