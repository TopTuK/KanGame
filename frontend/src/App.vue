<template>
  <div class="min-h-screen bg-board-bg text-slate-100">
    <router-view />
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

watch(locale, () => {
  document.title = t('app.title')
}, { immediate: true })
</script>
