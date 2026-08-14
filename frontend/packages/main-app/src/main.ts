import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createDAL } from '@animagus/shared'
import App from './App.vue'
import router from './router'
import { installMockApi } from './api/mock'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'
import '@fontsource/poppins/600.css'
import './styles/global.css'

const demoMode = import.meta.env.VITE_DEMO_MODE === 'true'
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
if (demoMode) installMockApi()
createDAL(demoMode, apiBaseUrl)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
