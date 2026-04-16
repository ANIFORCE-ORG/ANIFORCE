<script setup lang="ts">
import { ref } from 'vue'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import WelcomeStep from './onboarding/WelcomeStep.vue'
import ConnectPlatformStep from './onboarding/ConnectPlatformStep.vue'
import CreateProjectStep from './onboarding/CreateProjectStep.vue'
import PrepareCreativeStep from './onboarding/PrepareCreativeStep.vue'
import CreateCampaignStep from './onboarding/CreateCampaignStep.vue'

const emit = defineEmits<{
  complete: []
  skip: []
}>()

const currentStep = ref(0)
const totalSteps = 5

const steps = [
  { id: 0, title: '欢迎', component: 'WelcomeStep' },
  { id: 1, title: '连接平台', component: 'ConnectPlatformStep' },
  { id: 2, title: '创建项目', component: 'CreateProjectStep' },
  { id: 3, title: '准备素材', component: 'PrepareCreativeStep' },
  { id: 4, title: '创建投放', component: 'CreateCampaignStep' }
]

// 导航项
const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '工作台', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' }
]

const sessions = ref([
  { id: 'sess_onboarding', name: '新手引导', active: true }
])

const activePanel = ref('dashboard')
const activeSession = ref('sess_onboarding')
const chatInput = ref('')

// 对话消息 - 根据步骤动态变化
const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: '👋 欢迎来到 ANIFORCE！我是你的AI营销助手。\n\n让我带你快速了解平台的核心功能，只需4个简单步骤，你就可以开始使用了。'
  }
])

const quickHints = ref([
  '开始引导',
  '跳过引导',
  '了解更多',
  '查看功能'
])

const handleNext = () => {
  if (currentStep.value < totalSteps - 1) {
    currentStep.value++
    updateChatMessages()
  } else {
    emit('complete')
  }
}

const handlePrev = () => {
  if (currentStep.value > 0) {
    currentStep.value--
    updateChatMessages()
  }
}

const handleSkip = () => {
  emit('skip')
}

const handleStepComplete = (data?: any) => {
  console.log('步骤完成:', currentStep.value, data)
  handleNext()
}

const switchPanel = (item: any) => {
  // 引导期间禁用导航
  console.log('引导期间暂不支持切换面板')
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleSendMessage = (message: string) => {
  // 用户发送消息
  messages.value.push({
    role: 'user',
    author: '你',
    time: '刚刚',
    content: message
  })

  // 模拟AI回复
  setTimeout(() => {
    messages.value.push({
      role: 'assistant',
      author: 'ANIFORCE助手',
      time: '刚刚',
      content: getStepResponse(message)
    })
  }, 500)

  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  if (hint === '开始引导' && currentStep.value === 0) {
    handleNext()
  } else if (hint === '跳过引导') {
    handleSkip()
  } else {
    chatInput.value = hint
  }
}

// 根据步骤更新对话消息
const updateChatMessages = () => {
  const stepMessages = [
    {
      content: '👋 欢迎来到 ANIFORCE！我是你的AI营销助手。\n\n让我带你快速了解平台的核心功能，只需4个简单步骤，你就可以开始使用了。',
      hints: ['开始引导', '跳过引导', '了解更多', '查看功能']
    },
    {
      content: '🔗 第一步：连接广告平台\n\n连接你的广告账户后，系统会自动同步投放数据。我们支持：\n• Meta Ads (Facebook & Instagram)\n• Google Ads\n• TikTok Ads\n\n点击"立即连接"按钮开始授权。',
      hints: ['如何连接？', '安全吗？', '支持哪些平台？', '跳过此步']
    },
    {
      content: '📁 第二步：创建第一个项目\n\n项目是管理广告的基本单位，一个项目可以包含多个投放计划和素材。\n\n请填写：\n• 项目名称\n• 产品类型（游戏、应用、电商等）\n• 目标市场',
      hints: ['项目是什么？', '如何命名？', '可以修改吗？', '跳过此步']
    },
    {
      content: '🎨 第三步：准备素材\n\n你可以选择：\n• 上传现有素材（图片/视频）\n• 使用AI生成素材（4种方式）\n  - 全新生成\n  - 爆款二创\n  - 热点复刻\n  - 智能混剪',
      hints: ['AI生成是什么？', '支持什么格式？', '如何上传？', '跳过此步']
    },
    {
      content: '🚀 最后一步：创建投放计划\n\n设置你的第一个投放计划：\n• 投放计划名称\n• 选择投放平台\n• 设置日预算\n\n完成后，系统会帮你监控投放效果并提供优化建议！',
      hints: ['预算建议？', '如何优化？', '数据多久更新？', '完成引导']
    }
  ]

  const stepData = stepMessages[currentStep.value]
  messages.value.push({
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: stepData.content
  })
  quickHints.value = stepData.hints
}

// 根据用户消息返回回复
const getStepResponse = (message: string) => {
  const responses: Record<string, string> = {
    '如何连接？': '点击平台卡片上的"立即连接"按钮，会跳转到对应平台的授权页面。授权后，系统会自动同步你的广告数据。',
    '安全吗？': '完全安全！我们使用OAuth 2.0标准授权流程，不会存储你的账号密码。你可以随时在平台设置中撤销授权。',
    '支持哪些平台？': '目前支持Meta Ads、Google Ads和TikTok Ads。我们会持续增加更多平台支持。',
    '项目是什么？': '项目是组织和管理广告的容器。一个项目通常对应一个产品或一次营销活动，可以包含多个投放计划和素材。',
    '如何命名？': '建议使用清晰的命名，如"产品名+地区+目标"，例如"Candy Blast 美国iOS安装"。',
    '可以修改吗？': '当然可以！创建后随时可以在项目管理页面修改项目信息。',
    'AI生成是什么？': 'AI生成素材是我们的核心功能，可以根据你的需求自动生成广告素材，包括图片和视频。支持4种生成方式，适应不同场景。',
    '支持什么格式？': '支持常见的图片格式（JPG、PNG、GIF）和视频格式（MP4、MOV）。单个文件最大100MB。',
    '如何上传？': '点击"上传素材"按钮，选择文件即可。支持批量上传和拖拽上传。',
    '预算建议？': '建议从较小的预算开始测试（如$100-500/天），根据ROI表现逐步调整。系统会根据历史数据给出优化建议。',
    '如何优化？': '系统会实时监控投放效果，当ROI下降或CTR异常时，会自动提醒并给出优化建议，如更换素材、调整预算等。',
    '数据多久更新？': '数据每5分钟自动同步一次。你也可以点击刷新按钮手动同步。'
  }

  return responses[message] || '好的，如果有其他问题随时问我！你可以继续完成引导流程。'
}
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧导航栏 -->
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间内容区 -->
    <div class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- 进度指示器 -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white">新手引导</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400">
            步骤 {{ currentStep + 1 }} / {{ totalSteps }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <div
            v-for="(step, index) in steps"
            :key="step.id"
            class="w-8 h-1 rounded-full transition-colors"
            :class="index <= currentStep ? 'bg-primary' : 'bg-slate-200 dark:bg-slate-700'"
          ></div>
        </div>
      </div>

      <!-- 步骤内容 -->
      <div class="flex-1 overflow-y-auto">
        <WelcomeStep
          v-if="currentStep === 0"
          @next="handleNext"
          @skip="handleSkip"
        />
        <ConnectPlatformStep
          v-else-if="currentStep === 1"
          @next="handleStepComplete"
          @prev="handlePrev"
          @skip="handleSkip"
        />
        <CreateProjectStep
          v-else-if="currentStep === 2"
          @next="handleStepComplete"
          @prev="handlePrev"
          @skip="handleSkip"
        />
        <PrepareCreativeStep
          v-else-if="currentStep === 3"
          @next="handleStepComplete"
          @prev="handlePrev"
          @skip="handleSkip"
        />
        <CreateCampaignStep
          v-else-if="currentStep === 4"
          @complete="emit('complete')"
          @prev="handlePrev"
        />
      </div>
    </div>

    <!-- 右侧对话区 -->
    <ChatPanel
      :messages="messages"
      :quick-hints="quickHints"
      :chat-input="chatInput"
      @send-message="handleSendMessage"
      @hint-click="handleHintClick"
      @update:chat-input="chatInput = $event"
    />
  </div>
</template>
