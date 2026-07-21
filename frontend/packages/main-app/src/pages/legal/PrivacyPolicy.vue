<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    eyebrow: '隐私政策',
    title: 'Privacy Policy',
    updated: '最后更新：2026 年 7 月 18 日',
    intro:
      'ANIFORCE 是由 aniforce 拥有并运营的产品和品牌。本隐私政策适用于 ANIFORCE 官网、广告增长平台、Google Ads API、Meta Platform API 相关功能以及我们向客户提供的营销运营服务。',
    contact:
      '如需访问、更正、导出或删除个人信息、Google 用户数据、Google Ads 授权数据、Meta 平台数据或 Meta 授权数据，或有隐私、产品、业务、Google Ads API 和 Meta API 相关问题，请通过 support@aniforce.cc 联系我们。',
    sections: [
      {
        title: '1. 我们收集的信息',
        body: '我们可能收集你主动提交的联系信息，例如姓名、公司名称、职位、邮箱、电话和业务需求。对于已授权客户，我们也可能处理与组织、项目、广告账户、商务管理平台资产、主页、Threads 账号、广告系列、广告组、广告、素材、帖子、媒体内容、预算、投放状态、转化事件、互动数据、受众或粉丝数据、头像、账号元数据和广告效果相关的数据。',
      },
      {
        title: '2. 信息使用方式',
        body: '我们使用这些信息来回复咨询、提供产品演示、开通和管理客户账号、交付广告工作流服务、连接和管理已授权广告账户及商务资产、创建或更新广告计划、提交广告素材、生成报表、复盘投放表现、展示用户已授权的主页或 Threads 内容、排查故障、维护平台安全并提供优化建议。',
      },
      {
        title: '3. Google 用户数据和 Google Ads 数据',
        body: 'ANIFORCE 仅在用户或广告主明确授权后，通过 Google OAuth、Google Ads API 或客户提供的合法授权方式访问 Google 用户数据。我们可能访问和处理的 Google 用户数据包括 Google Ads 客户账号标识、账号名称、账号层级关系、广告系列、广告组、广告、素材、预算、投放状态、效果指标、转化相关指标、授权状态以及访问 Google Ads API 所需的 OAuth 凭证。此类数据仅用于客户授权的账号连接、广告管理、投放计划执行、报表、效果分析、客户支持和优化建议。',
      },
      {
        title: '4. Meta 平台数据',
        body: 'ANIFORCE 仅在用户、广告主、主页管理员或商务管理平台管理员明确授权后，通过 Meta Login、Meta Marketing API、Pages API、Threads API 或客户提供的合法授权方式访问 Meta 平台数据。我们可能访问和处理的 Meta 平台数据包括 Meta 商务管理平台资产、广告账户、主页、像素、资产关系、广告系列、广告组、广告、素材、预算、投放状态、成效指标、主页帖子、照片、视频、活动、主页元数据、粉丝或互动数据、PSID、头像、Threads 个人资料、Threads 帖子、媒体和文本内容、授权状态以及访问 Meta API 所需的访问令牌。此类数据仅用于客户授权的账号连接、资产管理、广告管理、主页管理、Threads 内容展示、投放计划执行、报表、效果分析、客户支持和优化建议。Threads 内容只会展示给创建该内容或授权访问该账号的用户，不会通过 ANIFORCE 对其他未授权用户公开。',
      },
      {
        title: '5. Google 和 Meta 平台数据的共享、传输和披露对象',
        body: '我们不会出售、出租、转售或以未经授权的广告画像为目的共享 Google 用户数据或 Meta 平台数据。我们仅在提供服务所必需、获得授权或法律要求的范围内共享、传输或披露此类数据，包括：向客户账号下获得授权的用户、客户指定的团队成员或客户代表展示相关数据；向 ANIFORCE 内部经授权的员工、媒体投放人员、客户成功人员和工程支持人员披露，以便提供广告管理、主页管理、Threads 内容展示、报表和技术支持；向云托管、数据库、文件存储、日志、安全、邮件、客户支持和数据处理服务提供商披露，这些服务提供商只能代表 ANIFORCE 处理数据并受保密和数据保护义务约束；在用户确认创建、更新或管理 Google Ads、Meta 广告、Meta 主页、Meta 商务资产或 Threads 相关资源时，向 Google、Meta 或相关 API 传输必要数据；在法律、监管、法院命令或保护 ANIFORCE、客户和用户安全所必要的情况下向主管机关或相关方披露。发生合并、收购、融资或资产转让时，相关数据可能作为业务资产转移，但接收方仍须遵守本政策或提供同等保护。',
      },
      {
        title: '6. 平台 API 使用限制',
        body: 'ANIFORCE 对从 Google API 接收的信息的使用和向其他应用的传输将遵守 Google API Services User Data Policy，包括 Limited Use 要求。ANIFORCE 对从 Meta Platform 接收的数据的使用将遵守 Meta Platform Terms、Developer Policies 和适用的权限使用要求。我们不会将 Google 用户数据或 Meta 平台数据用于训练通用人工智能模型、出售数据、未经授权的跨客户画像、未经授权的再识别，或与客户授权服务无关的目的。AI 辅助总结或优化建议仅在客户授权的数据范围内生成，并用于帮助客户理解和管理其自己的广告账户、主页、商务资产或内容表现。用于产品改进、营销分析或广告投放目的的成效分析仅使用无法识别身份或经过匿名处理的汇总信息，且不会用于重新识别用户身份。',
      },
      {
        title: '7. 敏感数据保护机制',
        body: '我们将 OAuth 访问令牌、刷新令牌、Meta 访问令牌、广告账号标识、商务资产标识、主页和 Threads 授权数据、PSID、头像、投放表现和客户业务数据视为敏感数据并采取保护措施。保护机制包括传输层加密、后端凭证管理、加密或受保护的存储、基于角色和组织的访问控制、最小权限原则、客户和项目级数据隔离、生产环境访问限制、审计和日志监控、员工保密义务以及对服务提供商的数据保护要求。Google OAuth 令牌和 Meta 访问令牌不会展示在前端页面，只有经过授权的后端服务可以在提供客户授权功能所需的范围内使用。',
      },
      {
        title: '8. 数据保留',
        body: '我们仅在实现本政策所述目的、维持客户账号、履行合同、提供支持、满足审计和法律义务所需期间保留个人信息、Google 用户数据和 Meta 平台数据。客户账号处于有效服务期内时，我们会保留必要的账号连接信息、授权状态、广告配置、主页或 Threads 连接信息和报表数据。客户终止服务、撤销授权或请求删除后，我们会删除或匿名化不再需要的平台数据；Google OAuth 令牌、Meta 访问令牌和账号连接凭证通常会在账号断开或删除请求确认后 30 天内移除，备份系统中的副本会按照备份周期在合理期限内清除，通常不超过 90 天，除非法律、争议解决、安全调查或合规义务要求更长保留。',
      },
      {
        title: '9. 数据删除和授权撤销',
        body: '用户可以在 ANIFORCE 平台中断开 Google Ads、Meta 广告账户、Meta 主页、Meta 商务资产或 Threads 账号授权，或通过 support@aniforce.cc 请求删除 Google 用户数据、Meta 平台数据或个人信息。收到可验证的删除请求后，我们会删除或匿名化与该请求相关且不再需要的数据，并停止继续通过相关授权访问平台数据。用户也可以通过 Google 账号安全设置或 Meta 账号、商务管理平台和应用设置撤销 ANIFORCE 的访问权限。对于 Meta Platform 数据删除请求，我们会按 Meta Platform 要求提供删除处理，并在完成后通过邮件或适用的回调/确认机制向用户确认。',
      },
      {
        title: '10. 跨境处理',
        body: '为提供全球广告管理、云托管、技术支持和安全服务，信息可能会在用户所在国家或地区以外被处理。我们会采取合同、访问控制和安全措施保护跨境处理的数据，并仅在提供服务或满足法律义务所需范围内进行处理。',
      },
      {
        title: '11. 联系方式',
        body: '法定注册公司名称：aniforce。官网：https://www.aniforce.cc。联系邮箱：support@aniforce.cc。',
      },
    ],
  },
  en: {
    eyebrow: 'Privacy Policy',
    title: 'Privacy Policy',
    updated: 'Last updated: July 18, 2026',
    intro:
      'ANIFORCE is a product and brand owned and operated by aniforce. This Privacy Policy applies to the ANIFORCE website, advertising growth platform, Google Ads API, Meta Platform API related features, and marketing operations services we provide to customers.',
    contact:
      'To access, correct, export, or delete personal information, Google user data, Google Ads authorization data, Meta Platform data, or Meta authorization data, or for privacy, product, business, Google Ads API, or Meta API related inquiries, please contact support@aniforce.cc.',
    sections: [
      {
        title: '1. Information We Collect',
        body: 'We may collect contact information that you submit to us, such as name, company name, role, email address, phone number, and business needs. For authorized customers, we may also process data related to organizations, projects, ad accounts, Business Manager assets, Pages, Threads accounts, campaigns, ad groups, ads, creatives, posts, media content, budgets, campaign status, conversion events, engagement data, audience or fan data, profile pictures, account metadata, and advertising performance.',
      },
      {
        title: '2. How We Use Information',
        body: 'We use this information to respond to inquiries, provide product demos, create and manage customer accounts, deliver advertising workflow services, connect and manage authorized ad accounts and business assets, create or update campaign plans, submit ad creatives, generate reports, review campaign performance, display authorized Page or Threads content, troubleshoot issues, maintain platform security, and provide optimization recommendations.',
      },
      {
        title: '3. Google User Data and Google Ads Data',
        body: 'ANIFORCE accesses Google user data only after a user or advertiser has provided explicit authorization through Google OAuth, the Google Ads API, or another lawful authorization method provided by the customer. Google user data we may access and process includes Google Ads customer account IDs, account names, account hierarchy, campaigns, ad groups, ads, creatives, budgets, campaign status, performance metrics, conversion-related metrics, authorization status, and OAuth credentials needed to access the Google Ads API. This data is used only for authorized account connection, campaign management, campaign plan execution, reporting, performance analysis, customer support, and optimization recommendations.',
      },
      {
        title: '4. Meta Platform Data',
        body: 'ANIFORCE accesses Meta Platform data only after a user, advertiser, Page administrator, or Business Manager administrator has provided explicit authorization through Meta Login, the Meta Marketing API, Pages API, Threads API, or another lawful authorization method provided by the customer. Meta Platform data we may access and process includes Meta Business Manager assets, ad accounts, Pages, pixels, asset relationships, campaigns, ad sets, ads, creatives, budgets, campaign status, performance metrics, Page posts, photos, videos, events, Page metadata, fan or engagement data, PSIDs, profile pictures, Threads profile information, Threads posts, media and text content, authorization status, and access tokens needed to access Meta APIs. This data is used only for authorized account connection, asset management, campaign management, Page management, Threads content display, campaign plan execution, reporting, performance analysis, customer support, and optimization recommendations. Threads content is displayed only to the user who created the content or authorized access to the account and is not made available through ANIFORCE to other unauthorized users.',
      },
      {
        title: '5. Sharing, Transfer, and Disclosure of Google and Meta Platform Data',
        body: 'We do not sell, rent, resell, or share Google user data or Meta Platform data for unauthorized advertising profiling. We share, transfer, or disclose such data only as necessary to provide the service, with authorization, or as required by law, including: displaying data to authorized users under the customer account, customer-designated team members, or customer representatives; disclosing data to authorized ANIFORCE employees, media buyers, customer success staff, and engineering support staff to provide campaign management, Page management, Threads content display, reporting, and technical support; disclosing data to cloud hosting, database, file storage, logging, security, email, customer support, and data processing providers that process data on behalf of ANIFORCE under confidentiality and data protection obligations; transmitting necessary data to Google, Meta, or related APIs when a user confirms the creation, update, or management of Google Ads, Meta ads, Meta Pages, Meta business assets, or Threads-related resources; and disclosing data to competent authorities or relevant parties when required by law, regulation, court order, or to protect the safety of ANIFORCE, customers, and users. In a merger, acquisition, financing, or asset transfer, data may be transferred as a business asset, but the recipient must continue to follow this Policy or provide equivalent protection.',
      },
      {
        title: '6. Platform API Use Restrictions',
        body: 'ANIFORCE use and transfer of information received from Google APIs will adhere to the Google API Services User Data Policy, including the Limited Use requirements. ANIFORCE use of data received from Meta Platform will adhere to the Meta Platform Terms, Developer Policies, and applicable permission usage requirements. We do not use Google user data or Meta Platform data to train general-purpose AI models, sell data, create unauthorized cross-customer profiles, perform unauthorized re-identification, or for purposes unrelated to the customer-authorized service. AI-assisted summaries or optimization recommendations are generated only within the scope of customer-authorized data and are used to help customers understand and manage their own ad accounts, Pages, business assets, or content performance. Performance analysis used for product improvement, marketing analytics, or advertising purposes is based only on aggregated, de-identified, or anonymized information that cannot reasonably be used to re-identify users.',
      },
      {
        title: '7. Sensitive Data Protection Mechanisms',
        body: 'We treat OAuth access tokens, refresh tokens, Meta access tokens, ad account identifiers, business asset identifiers, Page and Threads authorization data, PSIDs, profile pictures, campaign performance, and customer business data as sensitive data and apply protective measures. These measures include encryption in transit, backend credential management, encrypted or protected storage, role-based and organization-based access controls, least privilege access, customer and project-level data separation, production access restrictions, audit and log monitoring, employee confidentiality obligations, and data protection requirements for service providers. Google OAuth tokens and Meta access tokens are not exposed in frontend pages and may be used only by authorized backend services as necessary to provide customer-authorized features.',
      },
      {
        title: '8. Data Retention',
        body: 'We retain personal information, Google user data, and Meta Platform data only for as long as necessary to fulfill the purposes described in this Policy, maintain customer accounts, perform contracts, provide support, and meet audit and legal obligations. While a customer account is active, we retain necessary account connection information, authorization status, advertising configuration, Page or Threads connection information, and reporting data. After a customer terminates the service, revokes authorization, or requests deletion, we delete or anonymize platform data that is no longer needed. Google OAuth tokens, Meta access tokens, and account connection credentials are typically removed within 30 days after account disconnection or confirmation of a deletion request. Copies in backup systems are removed according to backup cycles within a reasonable period, typically no longer than 90 days, unless a longer retention period is required for legal, dispute resolution, security investigation, or compliance obligations.',
      },
      {
        title: '9. Data Deletion and Authorization Revocation',
        body: 'Users can disconnect Google Ads, Meta ad accounts, Meta Pages, Meta business assets, or Threads account authorization in the ANIFORCE platform, or request deletion of Google user data, Meta Platform data, or personal information by contacting support@aniforce.cc. After receiving a verifiable deletion request, we delete or anonymize data related to the request that is no longer needed and stop further access to platform data through the relevant authorization. Users may also revoke ANIFORCE access through their Google Account security settings or Meta account, Business Manager, and app settings. For Meta Platform data deletion requests, we process deletion in accordance with Meta Platform requirements and confirm completion by email or the applicable callback or confirmation mechanism.',
      },
      {
        title: '10. Cross-Border Processing',
        body: 'To provide global advertising management, cloud hosting, technical support, and security services, information may be processed outside the country or region where a user is located. We use contractual, access control, and security measures to protect data processed across borders and process it only as necessary to provide the service or meet legal obligations.',
      },
      {
        title: '11. Contact',
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
