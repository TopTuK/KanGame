import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import { i18n, setLocale } from './i18n/index.js'
import './assets/main.css'

setLocale(i18n.global.locale.value)

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(router)
app.mount('#app')
