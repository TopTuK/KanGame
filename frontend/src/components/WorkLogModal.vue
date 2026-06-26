<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="bg-slate-900 border border-slate-600 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col shadow-2xl">
      <div class="px-6 py-4 border-b border-slate-700 flex-shrink-0">
        <h2 class="text-xl font-bold text-white">{{ t('workLog.title') }}</h2>
      </div>
      <div class="px-6 py-4 overflow-y-auto flex-1 space-y-1 font-mono text-xs">
        <div v-for="(entry, i) in log" :key="i" class="text-slate-300">
          <template v-if="entry.type === 'work'">
            <span :class="workerColor(entry.worker_type)">{{ entry.worker_id?.toUpperCase() }}</span>
            → {{ entry.card_key }}:
            <span class="text-slate-500">{{ entry.roll }}</span>
            = <strong class="text-white">{{ entry.work }}</strong>
          </template>
          <template v-else-if="entry.type === 'deploy'">
            <span class="text-emerald-400">★ {{ entry.card_key }} deployed (Day {{ entry.day }})</span>
          </template>
          <template v-else-if="entry.type === 'advance'">
            <span class="text-sky-400">→ {{ entry.card_key }} → {{ entry.to }}</span>
          </template>
          <template v-else-if="entry.type === 'bonus'">
            <span class="text-amber-400">+{{ fmtRub(entry.amount) }} ({{ entry.card_key }})</span>
          </template>
          <template v-else-if="entry.type === 'penalty'">
            <span class="text-red-400">{{ fmtRub(entry.amount) }} ({{ entry.card_key }})</span>
          </template>
          <template v-else-if="entry.type === 'buff'">
            <span class="text-violet-400">{{ entry.card_key }}: +1 {{ entry.buff }} buff</span>
          </template>
        </div>
        <p v-if="!log.length" class="text-slate-500">{{ t('workLog.empty') }}</p>
      </div>
      <div class="px-6 py-4 border-t border-slate-700 flex justify-end flex-shrink-0">
        <button @click="$emit('close')" class="btn-primary px-6 py-2">{{ t('workLog.close') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
defineProps({ log: Array })
defineEmits(['close'])
const { t } = useI18n()

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}
function workerColor(type) {
  return { analyst: 'text-violet-400', developer: 'text-sky-400', tester: 'text-amber-400' }[type] || 'text-slate-400'
}
</script>
