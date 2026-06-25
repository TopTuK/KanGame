<template>
  <div class="min-h-screen bg-board-bg text-slate-100">
    <div class="fixed top-4 right-4 z-50">
      <LanguageSelector />
    </div>
    <router-view />
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import LanguageSelector from './components/LanguageSelector.vue'

const { t, locale } = useI18n()

watch(locale, () => {
  document.title = t('app.title')
}, { immediate: true })
</script>
