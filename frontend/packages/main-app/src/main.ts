import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createDAL } from '@aniforce/shared'
import App from './App.vue'
import router from './router'
import './styles/global.css'

const demoMode = import.meta.env.VITE_DEMO_MODE === 'true'
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
createDAL(demoMode, apiBaseUrl)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
