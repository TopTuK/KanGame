<template>
  <div class="p-4">
    <h3 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">{{ t('metrics.title') }}</h3>

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

    <!-- Day history bars -->
    <div v-if="metrics.length">
      <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('metrics.revenueByDay') }}</div>
      <div class="space-y-1 max-h-40 overflow-y-auto">
        <div
          v-for="m in [...metrics].reverse()"
          :key="m.day"
          class="flex items-center gap-2 text-xs"
        >
          <span class="text-slate-500 w-8 flex-shrink-0">D{{ m.day }}</span>
          <div class="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              class="h-full bg-emerald-500 rounded-full transition-all"
              :style="{ width: maxRevenue ? (m.daily_revenue / maxRevenue * 100) + '%' : '0%' }"
            ></div>
          </div>
          <span class="text-emerald-400 w-14 text-right font-mono">${{ m.daily_revenue }}</span>
        </div>
      </div>
    </div>
    <div v-else class="text-xs text-slate-600 text-center py-4">
      {{ t('metrics.noMetrics') }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'

const { t } = useI18n()
const store = useGameStore()

const metrics = computed(() => store.game?.metrics || [])
const cards = computed(() => store.game?.cards || [])

const deployedCount = computed(() => cards.value.filter(c => c.column === 'deployed').length)
const totalWip = computed(() => cards.value.filter(c => ['analysis', 'development', 'test'].includes(c.column)).length)
const dailyRevenue = computed(() =>
  cards.value.filter(c => c.column === 'deployed').reduce((s, c) => s + c.revenue_per_day, 0)
)
const latestThroughput = computed(() => {
  const ms = metrics.value
  return ms.length ? ms[ms.length - 1].throughput : 0
})
const maxRevenue = computed(() => Math.max(1, ...metrics.value.map(m => m.daily_revenue)))

const stats = computed(() => [
  { label: t('metrics.revPerDay'),   value: '$' + dailyRevenue.value,  color: 'text-emerald-400' },
  { label: t('metrics.deployed'),    value: deployedCount.value,        color: 'text-sky-400' },
  { label: t('metrics.wip'),         value: totalWip.value,             color: 'text-amber-400' },
  { label: t('metrics.throughput'),  value: latestThroughput.value,    color: 'text-violet-400' },
])

const cardTypes = computed(() => [
  { key: 'standard',   label: t('metrics.standard'),   color: 'bg-blue-700' },
  { key: 'expedite',   label: t('metrics.expedite'),   color: 'bg-red-700' },
  { key: 'fixed_date', label: t('metrics.fixedDate'),  color: 'bg-yellow-700' },
  { key: 'intangible', label: t('metrics.intangible'), color: 'bg-slate-600' },
  { key: 'bug',        label: t('metrics.bug'),        color: 'bg-orange-700' },
])

function countByType(type) {
  return cards.value.filter(c => c.card_type === type).length
}
</script>
