<template>
  <div>
    <!-- Key stats -->
    <div class="grid grid-cols-2 gap-2 mb-4">
      <div v-for="stat in stats" :key="stat.label" class="bg-slate-800/60 rounded-lg p-2.5 text-center border border-slate-700/30">
        <div class="text-xs text-slate-500 mb-0.5">{{ stat.label }}</div>
        <div :class="['text-lg font-bold font-mono', stat.color]">{{ stat.value }}</div>
      </div>
    </div>

    <!-- Legend -->
    <div class="space-y-1.5 mb-4">
      <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('metrics.cardTypes') }}</div>
      <div v-for="type in cardTypes" :key="type.key" class="flex items-center gap-2 text-xs">
        <div :class="['w-2.5 h-2.5 rounded-sm flex-shrink-0', type.color]"></div>
        <span class="text-slate-400 flex-1">{{ type.label }}</span>
        <span class="text-slate-300 font-mono">{{ countByType(type.key) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'

const { t } = useI18n()
const store = useGameStore()

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}

const cards = computed(() => store.game?.cards || [])
const metrics = computed(() => store.game?.metrics || [])

const deployedCount = computed(() =>
  cards.value.filter(c => ['deployed', 'exp_deployed'].includes(c.column)).length
)
const totalWip = computed(() =>
  cards.value.filter(c =>
    ['analysis', 'analysis_done', 'development', 'dev_done', 'test',
     'exp_analysis', 'exp_analysis_done', 'exp_development', 'exp_dev_done', 'exp_test'].includes(c.column)
  ).length
)
const dailyRevenue = computed(() =>
  cards.value
    .filter(c => c.column === 'deployed' && c.card_type === 'standard')
    .reduce((s, c) => s + (c.val || c.revenue_per_day || 0), 0)
)
const latestThroughput = computed(() => {
  const ms = metrics.value
  return ms.length ? ms[ms.length - 1].throughput : 0
})

const stats = computed(() => [
  { label: t('metrics.revPerDay'),   value: fmtRub(dailyRevenue.value),  color: 'text-emerald-400' },
  { label: t('metrics.deployed'),    value: deployedCount.value,        color: 'text-sky-400' },
  { label: t('metrics.wip'),         value: totalWip.value,             color: 'text-amber-400' },
  { label: t('metrics.throughput'),  value: latestThroughput.value,    color: 'text-violet-400' },
])

const cardTypes = computed(() => [
  { key: 'standard',   label: t('metrics.standard'),   color: 'bg-blue-600' },
  { key: 'fixed_date', label: t('metrics.fixedDate'),  color: 'bg-yellow-600' },
  { key: 'expedite',   label: t('metrics.expedite'),   color: 'bg-red-600' },
  { key: 'intangible', label: t('metrics.intangible'), color: 'bg-slate-500' },
])

function countByType(type) {
  return cards.value.filter(c => c.card_type === type).length
}
</script>
