<template>
  <div class="min-h-screen bg-board-bg text-slate-100">
    <router-view />
  </div>
</template>

<script setup>
import { watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from './stores/authStore.js'

const { t, locale } = useI18n()
const authStore = useAuthStore()

watch(locale, () => {
  document.title = t('app.title')
}, { immediate: true })

onMounted(() => {
  authStore.fetchMe()
})
</script>
