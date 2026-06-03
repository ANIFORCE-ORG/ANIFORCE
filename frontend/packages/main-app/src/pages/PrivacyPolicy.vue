<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    eyebrow: '隐私政策',
    title: 'Privacy Policy',
    updated: '最后更新：2026 年 6 月 3 日',
    intro: 'ANIFORCE 是由 aniforce 拥有并运营的产品和品牌。本隐私政策适用于 ANIFORCE 官网和服务。',
    contact: '如有隐私、产品、业务或 Google Ads API 相关问题，请通过 support@aniforce.cc 联系我们。',
    sections: [
      {
        title: '1. 我们收集的信息',
        body: '我们可能收集你主动提交的联系信息，例如姓名、公司名称、职位、邮箱、电话和业务需求。对于已授权客户，我们也可能处理与广告账户、项目、广告系列、素材和广告效果相关的数据。',
      },
      {
        title: '2. 信息使用方式',
        body: '我们使用这些信息来回复咨询、提供产品演示、交付广告工作流服务、管理授权广告账户、生成报表和提供优化建议。',
      },
      {
        title: '3. Google Ads 数据',
        body: 'ANIFORCE 仅在获得授权后访问 Google Ads 数据。Google Ads 数据仅用于广告管理、报表、效果分析和优化建议。我们不会出售、出租或转售 Google Ads 数据。',
      },
      {
        title: '4. 数据安全',
        body: '我们通过身份验证、权限控制和后端凭证管理来保护账户和广告数据。访问令牌不会展示在前端页面。',
      },
      {
        title: '5. 联系方式',
        body: '法定注册公司名称：aniforce。官网：https://www.aniforce.cc。联系邮箱：support@aniforce.cc。',
      },
    ],
  },
  en: {
    eyebrow: 'Privacy Policy',
    title: 'Privacy Policy',
    updated: 'Last updated: June 3, 2026',
    intro: 'ANIFORCE is a product and brand owned and operated by aniforce. This Privacy Policy applies to the ANIFORCE website and services.',
    contact: 'For privacy, product, business, or Google Ads API related inquiries, please contact support@aniforce.cc.',
    sections: [
      {
        title: '1. Information We Collect',
        body: 'We may collect contact information that you submit to us, such as name, company name, role, email address, phone number, and business needs. For authorized customers, we may also process data related to ad accounts, projects, campaigns, creatives, and advertising performance.',
      },
      {
        title: '2. How We Use Information',
        body: 'We use this information to respond to inquiries, provide product demos, deliver advertising workflow services, manage authorized ad accounts, generate reports, and provide optimization recommendations.',
      },
      {
        title: '3. Google Ads Data',
        body: 'ANIFORCE accesses Google Ads data only after authorization. Google Ads data is used only for campaign management, reporting, performance analysis, and optimization recommendations. We do not sell, rent, or resell Google Ads data.',
      },
      {
        title: '4. Data Security',
        body: 'We protect account and advertising data through authentication, permission controls, and backend credential management. Access tokens are not exposed in frontend pages.',
      },
      {
        title: '5. Contact',
        body: 'Legal Company Name: aniforce. Website: https://www.aniforce.cc. Contact Email: support@aniforce.cc.',
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
