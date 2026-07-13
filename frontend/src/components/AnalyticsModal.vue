<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="bg-slate-900 border border-slate-600 rounded-2xl max-w-4xl w-full shadow-2xl max-h-[85vh] flex flex-col">
      <div class="px-6 py-4 border-b border-slate-700 flex-shrink-0">
        <h2 class="text-xl font-bold text-white">{{ t('analytics.title') }}</h2>
      </div>

      <div class="px-6 py-5 overflow-y-auto space-y-6">
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('analytics.summary.title') }}</div>
          <div v-if="hasDeployed" class="grid grid-cols-3 sm:grid-cols-6 gap-3">
            <div v-for="tile in summaryTiles" :key="tile.label" class="text-center bg-slate-800/60 rounded-xl p-3">
              <div :class="['text-xl font-bold font-mono', tile.color]">{{ tile.value }}</div>
              <div class="text-[10px] text-slate-400 mt-1 leading-tight">{{ tile.label }}</div>
            </div>
          </div>
          <div v-else class="text-xs text-slate-600 text-center py-4 bg-slate-800/40 rounded-xl">
            {{ t('analytics.empty') }}
          </div>
        </div>

        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('analytics.cfd.title') }}</div>
          <div class="bg-slate-800/40 rounded-xl p-4">
            <CumulativeFlowChart :days="cfdDays" :series="cfdSeries" />
          </div>
        </div>

        <div v-if="hasDeployed" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('analytics.leadTime.title') }}</div>
            <div class="bg-slate-800/40 rounded-xl p-4">
              <DistributionHistogram :values="leadTimes" color="#34d399" :unit-label="t('analytics.axis.cards')" />
            </div>
          </div>
          <div>
            <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('analytics.cycleTime.title') }}</div>
            <div class="bg-slate-800/40 rounded-xl p-4">
              <DistributionHistogram :values="cycleTimes" color="#a78bfa" :unit-label="t('analytics.axis.cards')" />
            </div>
          </div>
        </div>
      </div>

      <div class="px-6 py-4 border-t border-slate-700 flex justify-end flex-shrink-0">
        <button @click="$emit('close')" class="btn-primary px-6 py-2">{{ t('workLog.close') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import CumulativeFlowChart from './CumulativeFlowChart.vue'
import DistributionHistogram from './DistributionHistogram.vue'

defineEmits(['close'])
const { t } = useI18n()
const store = useGameStore()

const STAGE_META = [
  { key: 'backlog', color: '#0c4a6e' },
  { key: 'ready', color: '#0369a1' },
  { key: 'analysis', color: '#0284c7' },
  { key: 'development', color: '#0ea5e9' },
  { key: 'test', color: '#38bdf8' },
  { key: 'deployed', color: '#7dd3fc' },
]

const game = computed(() => store.game)
const cards = computed(() => game.value?.cards || [])
const metrics = computed(() => game.value?.metrics || [])
const currentDay = computed(() => game.value?.current_day || 1)

const cfdDays = computed(() => {
  const days = []
  for (let d = 1; d <= currentDay.value; d++) days.push(d)
  return days
})

const cfdSeries = computed(() =>
  STAGE_META.map((stage) => ({
    key: stage.key,
    label: t(`analytics.stages.${stage.key}`),
    color: stage.color,
    data: cfdDays.value.map(
      (day) => cards.value.filter((c) => c.stage_days?.[stage.key] != null && c.stage_days[stage.key] <= day).length
    ),
  }))
)

const deployedCards = computed(() => cards.value.filter((c) => c.deployed_day != null))
const hasDeployed = computed(() => deployedCards.value.length > 0)

const leadTimes = computed(() =>
  deployedCards.value.filter((c) => c.entered_day != null).map((c) => c.deployed_day - c.entered_day)
)
const cycleTimes = computed(() =>
  deployedCards.value.map((c) => c.deployed_day - (c.stage_days?.analysis ?? c.entered_day ?? c.deployed_day))
)

function mean(arr) {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0
}

const avgLeadTime = computed(() => mean(leadTimes.value))
const avgCycleTime = computed(() => mean(cycleTimes.value))
const avgThroughput = computed(() => mean(metrics.value.map((m) => m.throughput)))
const avgWip = computed(() => mean(metrics.value.map((m) => m.wip)))
const littlesLawEstimate = computed(() => avgThroughput.value * avgLeadTime.value)

const onTimeRate = computed(() => {
  const critical = cards.value.filter(
    (c) => ['fixed_date', 'expedite'].includes(c.card_type) && (c.deployed_day != null || c.column === 'removed')
  )
  if (!critical.length) return null
  const onTime = critical.filter((c) => c.deployed_day != null && c.due_day != null && c.deployed_day <= c.due_day)
  return (onTime.length / critical.length) * 100
})

const summaryTiles = computed(() => [
  { label: t('analytics.metrics.avgLeadTime'), value: avgLeadTime.value.toFixed(1), color: 'text-emerald-400' },
  { label: t('analytics.metrics.avgCycleTime'), value: avgCycleTime.value.toFixed(1), color: 'text-violet-400' },
  { label: t('analytics.metrics.avgThroughput'), value: avgThroughput.value.toFixed(2), color: 'text-sky-400' },
  { label: t('analytics.metrics.avgWip'), value: avgWip.value.toFixed(1), color: 'text-amber-400' },
  {
    label: t('analytics.metrics.littlesLaw'),
    value: `${avgWip.value.toFixed(1)} ≈ ${littlesLawEstimate.value.toFixed(1)}`,
    color: 'text-slate-300',
  },
  {
    label: t('analytics.metrics.onTimeRate'),
    value: onTimeRate.value == null ? '—' : `${onTimeRate.value.toFixed(0)}%`,
    color: 'text-rose-300',
  },
])
</script>
