# ANIMAGUS 开发规范与技能指南

## 核心原则

### 1. 系统架构：三列布局
**所有功能必须遵循三列布局架构，禁止创建独立全屏页面**

```
┌─────────────┬──────────────────────┬─────────────┐
│  左侧导航栏  │   中间内容区域        │  右侧对话框  │
│  SidebarNav │   Dynamic Content    │  ChatPanel  │
└─────────────┴──────────────────────┴─────────────┘
```

#### 允许的独立页面（例外）
- 登录页面 (`/login`)
- 404/错误页面
- 首次引导流程（特殊全屏体验）

#### 禁止的做法 ❌
```typescript
// ❌ 错误：创建独立的全屏页面
{
  path: '/reports',
  component: () => import('@/pages/Reports.vue')
}

// ❌ 错误：创建独立的平台连接页面
{
  path: '/platform-connect',
  component: () => import('@/pages/PlatformConnect.vue')
}
```

#### 正确的做法 ✅
```typescript
// ✅ 正确：使用查询参数切换内容
{
  path: '/dashboard',
  component: () => import('@/pages/Dashboard.vue')
  // 通过 ?panel=reports 切换到报表视图
}

// ✅ 正确：在现有组件中集成功能
// WorkspaceDashboard.vue 中动态渲染不同内容
<ReportsContent v-if="activePanel === 'reports'" />
```

---

## 开发流程规范

### Step 1: 需求分析
在开始编码前，明确：
1. 这个功能是否需要独立页面？（99%情况下答案是"否"）
2. 应该集成到哪个现有组件中？
3. 是否需要新的导航项？

### Step 2: 对比旧系统
**必须先查看旧系统实现，再开始开发**

```bash
# 旧系统路径（Vanilla JS）
/Users/PJlai/Desktop/ANIMAGUS/

# 新系统路径（Vue3）
/Users/PJlai/Desktop/ANIMAGUS_remote/
```

#### 对比检查清单
- [ ] 旧系统中这个功能是如何布局的？
- [ ] 是独立页面还是嵌入式组件？
- [ ] 有哪些交互逻辑和数据流？
- [ ] 使用了哪些 API 接口？
- [ ] 有哪些边界情况需要处理？

#### 常见文件对应关系
| 功能 | 旧系统 | 新系统 |
|-----|-------|-------|
| 路由 | `frontend/js/router.js` | `frontend/packages/main-app/src/router/index.ts` |
| 状态 | `frontend/js/state.js` | `frontend/packages/main-app/src/store/*.ts` |
| 面板 | `frontend/js/panels/*.js` | `frontend/packages/main-app/src/components/home/workspace/*.vue` |
| API | `backend/app/api/v1/*.py` | `backend/app/api/v1/*.py` |

### Step 3: 设计集成方案
根据功能类型选择集成方式：

#### 类型 A: 工作台功能（如数据报表）
```vue
<!-- WorkspaceDashboard.vue -->
<script setup>
const activePanel = ref('dashboard')

const navItems = [
  { id: 'dashboard', label: '工作台', path: '/dashboard' },
  { id: 'reports', label: '数据报表', path: '/dashboard?panel=reports' }
]

watch(() => route.query.panel, (newPanel) => {
  activePanel.value = newPanel || 'dashboard'
}, { immediate: true })
</script>

<template>
  <div class="three-column-layout">
    <SidebarNav :nav-items="navItems" />

    <main>
      <div v-if="activePanel === 'dashboard'">
        <!-- 工作台内容 -->
      </div>
      <ReportsContent v-else-if="activePanel === 'reports'" />
    </main>

    <ChatPanel />
  </div>
</template>
```

#### 类型 B: 嵌入式功能（如平台连接）
不创建新页面，在现有组件中添加功能：
- 引导流程：`ConnectPlatformStep.vue`
- 工作台：`PlatformStatus.vue`

```vue
<!-- PlatformStatus.vue -->
<script setup>
const handleConnect = async (platform) => {
  const { auth_url } = await axios.post(`/api/v1/platform/connect?platform=${platform.id}`)
  window.open(auth_url, '_blank', 'width=600,height=700')
}
</script>

<template>
  <div class="platform-status">
    <button v-if="!platform.connected" @click="handleConnect(platform)">
      立即连接
    </button>
  </div>
</template>
```

### Step 4: 实现与测试
1. 创建组件文件（在 `components/` 而非 `pages/`）
2. 集成到现有布局中
3. 测试三列布局是否正常
4. 测试响应式和交互逻辑

### Step 5: 代码审查检查清单
- [ ] 是否遵循三列布局架构？
- [ ] 是否创建了不必要的独立页面？
- [ ] 是否对比了旧系统实现？
- [ ] 组件是否可复用？
- [ ] 是否使用了 Pinia 进行状态管理？
- [ ] API 调用是否正确？
- [ ] 错误处理是否完善？

---

## 技术规范

### 1. 组件命名与组织
```
frontend/packages/main-app/src/
├── components/
│   ├── home/
│   │   ├── workspace/          # 工作台相关组件
│   │   │   ├── TodayOverview.vue
│   │   │   ├── ReportsContent.vue
│   │   │   └── PlatformStatus.vue
│   │   └── onboarding/         # 引导流程组件
│   │       └── ConnectPlatformStep.vue
│   └── layout/                 # 布局组件
│       ├── SidebarNav.vue
│       └── ChatPanel.vue
├── pages/                      # 仅用于路由入口
│   ├── Dashboard.vue           # 三列布局容器
│   ├── Login.vue               # 特殊独立页面
│   └── Home.vue
└── store/                      # Pinia 状态管理
    ├── projects.ts
    ├── campaigns.ts
    └── creatives.ts
```

### 2. 路由设计原则
```typescript
// ✅ 推荐：使用查询参数切换视图
'/dashboard?panel=reports'
'/dashboard?panel=insights'

// ✅ 推荐：使用动态路由参数
'/projects/:id'
'/campaigns/:id'

// ❌ 避免：为每个功能创建独立路由
'/reports'           // 应该是 /dashboard?panel=reports
'/platform-connect'  // 应该集成到现有组件中
```

### 3. 状态管理模式
```typescript
// store/campaigns.ts
import { defineStore } from 'pinia'

export const useCampaignsStore = defineStore('campaigns', {
  state: () => ({
    campaigns: [],
    loading: false
  }),

  actions: {
    async fetchCampaigns() {
      this.loading = true
      try {
        const response = await axios.get('/api/v1/campaigns')
        this.campaigns = response.data
      } finally {
        this.loading = false
      }
    }
  }
})
```

### 4. API 调用规范
```typescript
// ✅ 正确：在组件中直接使用 axios
import axios from 'axios'

const handleConnect = async (platform: Platform) => {
  try {
    const response = await axios.post(`/api/v1/platform/connect?platform=${platform.id}`)
    window.open(response.data.auth_url, '_blank')
  } catch (error) {
    console.error('Failed to connect:', error)
    // 显示错误提示
  }
}

// ✅ 正确：在 store 中封装复杂逻辑
const campaignsStore = useCampaignsStore()
await campaignsStore.fetchCampaigns()
```

### 5. 样式规范
```vue
<template>
  <!-- 使用 Tailwind CSS 工具类 -->
  <div class="flex h-screen bg-slate-50 dark:bg-slate-950">
    <aside class="w-64 border-r border-slate-200 dark:border-slate-800">
      <!-- 左侧导航 -->
    </aside>

    <main class="flex-1 overflow-y-auto">
      <!-- 中间内容 -->
    </main>

    <aside class="w-80 border-l border-slate-200 dark:border-slate-800">
      <!-- 右侧对话 -->
    </aside>
  </div>
</template>
```

---

## 常见错误与解决方案

### 错误 1: 创建独立页面
**症状**: 创建了 `pages/Reports.vue` 并添加路由 `/reports`

**解决方案**:
1. 删除独立页面文件
2. 创建 `components/home/workspace/ReportsContent.vue`
3. 在 `WorkspaceDashboard.vue` 中集成
4. 使用查询参数 `?panel=reports` 切换

### 错误 2: 忽略旧系统实现
**症状**: 直接开发新功能，结果与旧系统逻辑不一致

**解决方案**:
1. 先查看 `/Users/PJlai/Desktop/ANIMAGUS` 中的对应文件
2. 理解原有的数据流和交互逻辑
3. 在新系统中复现相同的功能
4. 使用 Vue3 和 TypeScript 改进实现

### 错误 3: 破坏三列布局
**症状**: 新功能占据全屏，导航栏和对话框消失

**解决方案**:
1. 确保所有内容都在 `WorkspaceDashboard.vue` 的中间区域渲染
2. 不要使用 `router.push()` 跳转到新页面
3. 使用 `activePanel` 状态切换内容

### 错误 4: 重复造轮子
**症状**: 创建新的 API 调用逻辑，但 store 中已有类似功能

**解决方案**:
1. 检查 `src/store/` 中是否已有相关 store
2. 复用现有的 actions 和 getters
3. 如需扩展，在现有 store 中添加新方法

---

## 快速参考

### 开发新功能前的自检清单
- [ ] 我是否查看了旧系统的实现？
- [ ] 这个功能是否真的需要独立页面？
- [ ] 我是否遵循了三列布局架构？
- [ ] 我是否复用了现有的组件和 store？
- [ ] 我的路由设计是否合理？
- [ ] 我的代码是否符合 Vue3 + TypeScript 规范？

### 关键路径速查
```bash
# 旧系统（参考用）
/Users/PJlai/Desktop/ANIMAGUS/

# 新系统（开发用）
/Users/PJlai/Desktop/ANIMAGUS_remote/

# 前端主要目录
frontend/packages/main-app/src/
  ├── components/home/workspace/  # 工作台组件
  ├── components/layout/          # 布局组件
  ├── pages/                      # 路由入口
  ├── store/                      # 状态管理
  └── router/                     # 路由配置

# 后端主要目录
backend/app/
  ├── api/v1/                     # API 路由
  ├── connectors/                 # 平台适配器
  └── models/                     # 数据模型
```

### 常用命令
```bash
# 启动前端开发服务器
cd /Users/PJlai/Desktop/ANIMAGUS_remote/frontend
npm run dev

# 启动后端服务器
cd /Users/PJlai/Desktop/ANIMAGUS_remote/backend
uvicorn app.main:app --reload

# Git 提交
git add -A
git commit -m "feat: 功能描述"
git push origin master
```

---

## 总结

**记住这三个核心原则**:
1. **三列布局是王道** - 不要创建独立页面
2. **先看旧系统再开发** - 避免重复劳动和逻辑不一致
3. **组件化思维** - 一切皆组件，复用优于重写

遵循这些规范，可以确保代码质量、架构一致性和开发效率。
