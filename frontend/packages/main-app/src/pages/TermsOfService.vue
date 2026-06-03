<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    eyebrow: '服务条款',
    title: 'Terms of Service',
    updated: '最后更新：2026 年 6 月 3 日',
    intro: '本服务条款由你与 aniforce 订立。aniforce 是 ANIFORCE 产品和品牌的拥有者及运营方。',
    contact: '如有服务、产品、隐私或 Google Ads API 相关问题，请通过 support@aniforce.cc 联系我们。',
    sections: [
      {
        title: '1. 服务说明',
        body: 'ANIFORCE 提供 AI 驱动的广告工作流工具，用于项目管理、素材管理、广告账户连接、广告系列管理、效果报表和优化建议。',
      },
      {
        title: '2. 授权账户访问',
        body: '用户只能连接和管理其有权访问的广告账户。ANIFORCE 仅在用户或客户授权范围内访问广告平台数据。',
      },
      {
        title: '3. Google Ads API 使用',
        body: 'ANIFORCE 使用 Google Ads API 来连接授权账户、读取账户和广告效果数据、创建或更新广告系列、广告组、广告、预算和状态。任何会影响广告账户的操作均应由授权用户确认后执行。',
      },
      {
        title: '4. 用户责任',
        body: '用户应确保提交的信息真实准确，并确保其拥有连接广告账户、管理广告活动和共享相关数据的合法权限。',
      },
      {
        title: '5. 公司信息',
        body: '法定注册公司名称：aniforce。ANIFORCE 是由 aniforce 拥有并运营的产品和品牌。官网：https://www.aniforce.cc。联系邮箱：support@aniforce.cc。',
      },
    ],
  },
  en: {
    eyebrow: 'Terms of Service',
    title: 'Terms of Service',
    updated: 'Last updated: June 3, 2026',
    intro: 'These Terms of Service are entered into between you and aniforce. aniforce is the owner and operator of the ANIFORCE product and brand.',
    contact: 'For service, product, privacy, or Google Ads API related inquiries, please contact support@aniforce.cc.',
    sections: [
      {
        title: '1. Service Description',
        body: 'ANIFORCE provides AI-driven advertising workflow tools for project management, creative management, ad account connection, campaign management, performance reporting, and optimization recommendations.',
      },
      {
        title: '2. Authorized Account Access',
        body: 'Users may only connect and manage ad accounts that they are authorized to access. ANIFORCE accesses advertising platform data only within the authorization granted by the user or customer.',
      },
      {
        title: '3. Google Ads API Use',
        body: 'ANIFORCE uses the Google Ads API to connect authorized accounts, retrieve account and advertising performance data, and create or update campaigns, ad groups, ads, budgets, and status. Any operation that affects an ad account should be executed only after confirmation by an authorized user.',
      },
      {
        title: '4. User Responsibilities',
        body: 'Users are responsible for providing accurate information and ensuring they have the legal authority to connect ad accounts, manage advertising activity, and share related data.',
      },
      {
        title: '5. Company Information',
        body: 'Legal Company Name: aniforce. ANIFORCE is a product and brand owned and operated by aniforce. Website: https://www.aniforce.cc. Contact Email: support@aniforce.cc.',
      },
    ],
  },
}

const pageCopy = computed(() => copy[language.value])
</script>

<template>
  <main class="bg-background-light px-6 py-14 text-slate-950 lg:px-10">
    <article class="mx-auto max-w-4xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:p-10">
      <p class="text-sm font-semibold uppercase tracking-[0.22em] text-primary">{{ pageCopy.eyebrow }}</p>
      <h1 class="mt-4 text-3xl font-black leading-tight md:text-4xl">{{ pageCopy.title }}</h1>
      <p class="mt-3 text-sm text-slate-500">{{ pageCopy.updated }}</p>
      <p class="mt-8 text-base leading-8 text-slate-700">{{ pageCopy.intro }}</p>
      <section v-for="section in pageCopy.sections" :key="section.title" class="mt-8">
        <h2 class="text-xl font-bold text-slate-950">{{ section.title }}</h2>
        <p class="mt-3 text-base leading-8 text-slate-700">{{ section.body }}</p>
      </section>
      <div class="mt-10 rounded-lg border border-blue-100 bg-blue-50 p-5 text-sm leading-7 text-slate-700">
        {{ pageCopy.contact }}
      </div>
    </article>
  </main>
</template>
