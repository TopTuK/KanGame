<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="bg-slate-900 border border-slate-600 rounded-2xl max-w-lg w-full shadow-2xl">
      <div class="px-6 py-4 border-b border-slate-700">
        <h2 class="text-xl font-bold text-white">{{ t('help.title') }}</h2>
      </div>
      <div class="px-6 py-5 text-sm text-slate-300 space-y-3 leading-relaxed">
        <p>{{ t('help.intro') }}</p>
        <ul class="list-disc list-inside space-y-1 text-slate-400">
          <li>{{ t('help.pull') }}</li>
          <li>{{ t('help.assign') }}</li>
          <li>{{ t('help.startWork') }}</li>
          <li>{{ t('help.endDay') }}</li>
        </ul>
        <p class="text-amber-300 font-medium">{{ t('help.f1deadline') }}</p>
      </div>
      <div class="px-6 py-4 border-t border-slate-700 flex justify-end">
        <button @click="$emit('close')" class="btn-primary px-6 py-2">{{ t('help.gotIt') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
defineEmits(['close'])
const { t } = useI18n()
</script>
