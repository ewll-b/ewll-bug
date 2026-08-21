import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ArcoVue from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import './styles/main.css'
import App from './App.vue'
import router from './router'

const app = createApp(App).use(createPinia()).use(router).use(ArcoVue)

// 等待首个异步路由解析完成，避免登录页短暂挂载受保护的应用壳层。
router.isReady().then(() => app.mount('#app'))
