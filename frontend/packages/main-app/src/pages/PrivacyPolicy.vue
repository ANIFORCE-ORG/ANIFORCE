<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    eyebrow: '隐私政策',
    title: 'Privacy Policy',
    updated: '最后更新：2026 年 7 月 17 日',
    intro: 'ANIFORCE 是由 aniforce 拥有并运营的产品和品牌。本隐私政策适用于 ANIFORCE 官网、广告增长平台、Google Ads API 相关功能以及我们向客户提供的营销运营服务。',
    contact: '如需访问、更正、导出或删除个人信息、Google 用户数据或 Google Ads 授权数据，或有隐私、产品、业务和 Google Ads API 相关问题，请通过 support@aniforce.cc 联系我们。',
    sections: [
      {
        title: '1. 我们收集的信息',
        body: '我们可能收集你主动提交的联系信息，例如姓名、公司名称、职位、邮箱、电话和业务需求。对于已授权客户，我们也可能处理与组织、项目、广告账户、广告系列、广告组、广告、素材、预算、投放状态、转化事件和广告效果相关的数据。',
      },
      {
        title: '2. 信息使用方式',
        body: '我们使用这些信息来回复咨询、提供产品演示、开通和管理客户账号、交付广告工作流服务、管理已授权广告账户、创建或更新广告计划、提交广告素材、生成报表、复盘投放表现、排查故障、维护平台安全并提供优化建议。',
      },
      {
        title: '3. Google 用户数据和 Google Ads 数据',
        body: 'ANIFORCE 仅在用户或广告主明确授权后，通过 Google OAuth、Google Ads API 或客户提供的合法授权方式访问 Google 用户数据。我们可能访问和处理的 Google 用户数据包括 Google Ads 客户账号标识、账号名称、账号层级关系、广告系列、广告组、广告、素材、预算、投放状态、效果指标、转化相关指标、授权状态以及访问 Google Ads API 所需的 OAuth 凭证。此类数据仅用于客户授权的账号连接、广告管理、投放计划执行、报表、效果分析、客户支持和优化建议。',
      },
      {
        title: '4. Google 用户数据的共享、传输和披露对象',
        body: '我们不会出售、出租、转售或以广告画像为目的共享 Google 用户数据。我们仅在提供服务所必需、获得授权或法律要求的范围内共享、传输或披露 Google 用户数据，包括：向客户账号下获得授权的用户、客户指定的团队成员或客户代表展示相关数据；向 ANIFORCE 内部经授权的员工、媒体投放人员、客户成功人员和工程支持人员披露，以便提供广告管理、报表和技术支持；向云托管、数据库、文件存储、日志、安全、邮件、客户支持和数据处理服务提供商披露，这些服务提供商只能代表 ANIFORCE 处理数据并受保密和数据保护义务约束；在用户确认创建、更新或管理 Google Ads 资源时向 Google 或 Google Ads API 传输必要数据；在法律、监管、法院命令或保护 ANIFORCE、客户和用户安全所必要的情况下向主管机关或相关方披露。发生合并、收购、融资或资产转让时，相关数据可能作为业务资产转移，但接收方仍须遵守本政策或提供同等保护。',
      },
      {
        title: '5. Google API 使用限制',
        body: 'ANIFORCE 对从 Google API 接收的信息的使用和向其他应用的传输将遵守 Google API Services User Data Policy，包括 Limited Use 要求。我们不会将 Google 用户数据用于训练通用人工智能模型、广告再定向、跨客户画像、出售数据或与客户授权服务无关的目的。AI 辅助总结或优化建议仅在客户授权的数据范围内生成，并用于帮助客户理解和管理其自己的广告账户。',
      },
      {
        title: '6. 敏感数据保护机制',
        body: '我们将 OAuth 访问令牌、刷新令牌、广告账号标识、投放表现和客户业务数据视为敏感数据并采取保护措施。保护机制包括传输层加密、后端凭证管理、加密或受保护的存储、基于角色和组织的访问控制、最小权限原则、客户和项目级数据隔离、生产环境访问限制、审计和日志监控、员工保密义务以及对服务提供商的数据保护要求。Google OAuth 令牌不会展示在前端页面，只有经过授权的后端服务可以在提供客户授权功能所需的范围内使用。',
      },
      {
        title: '7. 数据保留',
        body: '我们仅在实现本政策所述目的、维持客户账号、履行合同、提供支持、满足审计和法律义务所需期间保留个人信息和 Google 用户数据。客户账号处于有效服务期内时，我们会保留必要的账号连接信息、授权状态、广告配置和报表数据。客户终止服务、撤销授权或请求删除后，我们会删除或匿名化不再需要的 Google 用户数据；OAuth 令牌和账号连接凭证通常会在账号断开或删除请求确认后 30 天内移除，备份系统中的副本会按照备份周期在合理期限内清除，通常不超过 90 天，除非法律、争议解决、安全调查或合规义务要求更长保留。',
      },
      {
        title: '8. 数据删除和授权撤销',
        body: '用户可以在 ANIFORCE 平台中断开 Google Ads 账号授权，或通过 support@aniforce.cc 请求删除 Google 用户数据。收到可验证的删除请求后，我们会删除或匿名化与该请求相关且不再需要的数据，并停止继续通过相关授权访问 Google Ads 数据。用户也可以通过 Google 账号安全设置撤销 ANIFORCE 的 Google 访问权限。',
      },
      {
        title: '9. 跨境处理',
        body: '为提供全球广告管理、云托管、技术支持和安全服务，信息可能会在用户所在国家或地区以外被处理。我们会采取合同、访问控制和安全措施保护跨境处理的数据，并仅在提供服务或满足法律义务所需范围内进行处理。',
      },
      {
        title: '10. 联系方式',
        body: '法定注册公司名称：aniforce。官网：https://www.aniforce.cc。联系邮箱：support@aniforce.cc。',
      },
    ],
  },
  en: {
    eyebrow: 'Privacy Policy',
    title: 'Privacy Policy',
    updated: 'Last updated: July 17, 2026',
    intro: 'ANIFORCE is a product and brand owned and operated by aniforce. This Privacy Policy applies to the ANIFORCE website, advertising growth platform, Google Ads API related features, and marketing operations services we provide to customers.',
    contact: 'To access, correct, export, or delete personal information, Google user data, or Google Ads authorization data, or for privacy, product, business, or Google Ads API related inquiries, please contact support@aniforce.cc.',
    sections: [
      {
        title: '1. Information We Collect',
        body: 'We may collect contact information that you submit to us, such as name, company name, role, email address, phone number, and business needs. For authorized customers, we may also process data related to organizations, projects, ad accounts, campaigns, ad groups, ads, creatives, budgets, campaign status, conversion events, and advertising performance.',
      },
      {
        title: '2. How We Use Information',
        body: 'We use this information to respond to inquiries, provide product demos, create and manage customer accounts, deliver advertising workflow services, manage authorized ad accounts, create or update campaign plans, submit ad creatives, generate reports, review campaign performance, troubleshoot issues, maintain platform security, and provide optimization recommendations.',
      },
      {
        title: '3. Google User Data and Google Ads Data',
        body: 'ANIFORCE accesses Google user data only after a user or advertiser has provided explicit authorization through Google OAuth, the Google Ads API, or another lawful authorization method provided by the customer. Google user data we may access and process includes Google Ads customer account IDs, account names, account hierarchy, campaigns, ad groups, ads, creatives, budgets, campaign status, performance metrics, conversion-related metrics, authorization status, and OAuth credentials needed to access the Google Ads API. This data is used only for authorized account connection, campaign management, campaign plan execution, reporting, performance analysis, customer support, and optimization recommendations.',
      },
      {
        title: '4. Sharing, Transfer, and Disclosure of Google User Data',
        body: 'We do not sell, rent, resell, or share Google user data for advertising profiling. We share, transfer, or disclose Google user data only as necessary to provide the service, with authorization, or as required by law, including: displaying data to authorized users under the customer account, customer-designated team members, or customer representatives; disclosing data to authorized ANIFORCE employees, media buyers, customer success staff, and engineering support staff to provide campaign management, reporting, and technical support; disclosing data to cloud hosting, database, file storage, logging, security, email, customer support, and data processing providers that process data on behalf of ANIFORCE under confidentiality and data protection obligations; transmitting necessary data to Google or the Google Ads API when a user confirms the creation, update, or management of Google Ads resources; and disclosing data to competent authorities or relevant parties when required by law, regulation, court order, or to protect the safety of ANIFORCE, customers, and users. In a merger, acquisition, financing, or asset transfer, data may be transferred as a business asset, but the recipient must continue to follow this Policy or provide equivalent protection.',
      },
      {
        title: '5. Google API Limited Use',
        body: 'ANIFORCE use and transfer of information received from Google APIs will adhere to the Google API Services User Data Policy, including the Limited Use requirements. We do not use Google user data to train general-purpose AI models, retarget advertising, build cross-customer profiles, sell data, or for purposes unrelated to the customer-authorized service. AI-assisted summaries or optimization recommendations are generated only within the scope of customer-authorized data and are used to help customers understand and manage their own advertising accounts.',
      },
      {
        title: '6. Sensitive Data Protection Mechanisms',
        body: 'We treat OAuth access tokens, refresh tokens, ad account identifiers, campaign performance, and customer business data as sensitive data and apply protective measures. These measures include encryption in transit, backend credential management, encrypted or protected storage, role-based and organization-based access controls, least privilege access, customer and project-level data separation, production access restrictions, audit and log monitoring, employee confidentiality obligations, and data protection requirements for service providers. Google OAuth tokens are not exposed in frontend pages and may be used only by authorized backend services as necessary to provide customer-authorized features.',
      },
      {
        title: '7. Data Retention',
        body: 'We retain personal information and Google user data only for as long as necessary to fulfill the purposes described in this Policy, maintain customer accounts, perform contracts, provide support, and meet audit and legal obligations. While a customer account is active, we retain necessary account connection information, authorization status, advertising configuration, and reporting data. After a customer terminates the service, revokes authorization, or requests deletion, we delete or anonymize Google user data that is no longer needed. OAuth tokens and account connection credentials are typically removed within 30 days after account disconnection or confirmation of a deletion request. Copies in backup systems are removed according to backup cycles within a reasonable period, typically no longer than 90 days, unless a longer retention period is required for legal, dispute resolution, security investigation, or compliance obligations.',
      },
      {
        title: '8. Data Deletion and Authorization Revocation',
        body: 'Users can disconnect a Google Ads account in the ANIFORCE platform or request deletion of Google user data by contacting support@aniforce.cc. After receiving a verifiable deletion request, we delete or anonymize data related to the request that is no longer needed and stop further access to Google Ads data through the relevant authorization. Users may also revoke ANIFORCE Google access through their Google Account security settings.',
      },
      {
        title: '9. Cross-Border Processing',
        body: 'To provide global advertising management, cloud hosting, technical support, and security services, information may be processed outside the country or region where a user is located. We use contractual, access control, and security measures to protect data processed across borders and process it only as necessary to provide the service or meet legal obligations.',
      },
      {
        title: '10. Contact',
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
