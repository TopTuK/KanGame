<template>
  <header class="flex-shrink-0 bg-slate-900 border-b border-slate-700/60">
    <div class="px-5 py-2.5 flex items-center gap-4">
      <router-link to="/" class="flex items-center gap-2 hover:opacity-80 transition-opacity flex-shrink-0">
        <div class="w-7 h-7 rounded-md bg-sky-500 flex items-center justify-center font-bold text-xs text-white">K</div>
        <span class="text-white font-bold text-base leading-none">KanGame</span>
      </router-link>

      <span
        v-if="store.game?.is_demo"
        class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-950/60 text-amber-400 border border-amber-800/50 flex-shrink-0"
      >{{ t('demo.badge') }}</span>

      <div class="h-5 w-px bg-slate-700 flex-shrink-0"></div>

      <div v-if="store.game" class="flex items-center gap-3 flex-shrink-0">
        <div class="text-center">
          <div class="text-[10px] text-slate-500 uppercase tracking-wider leading-none mb-0.5">{{ t('header.day') }}</div>
          <div class="text-xl font-bold font-mono text-sky-400 leading-none">
            {{ store.game.current_day }}<span class="text-slate-600 text-sm">/{{ store.game.total_days }}</span>
          </div>
        </div>
        <div class="w-24">
          <div class="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div class="h-full bg-sky-500 rounded-full transition-all duration-500" :style="{ width: progress + '%' }"></div>
          </div>
          <div class="text-[10px] text-slate-600 mt-0.5 text-center">{{ Math.round(progress) }}%</div>
        </div>
      </div>

      <div v-if="store.game" class="h-5 w-px bg-slate-700 flex-shrink-0"></div>

      <div v-if="store.game" class="flex items-center gap-5 flex-shrink-0">
        <div>
          <div class="text-[10px] text-slate-500 uppercase tracking-wider leading-none mb-0.5">{{ t('header.totalRevenue') }}</div>
          <div class="text-lg font-bold text-emerald-400 font-mono leading-none">{{ fmtRub(store.game.total_revenue) }}</div>
        </div>
        <div>
          <div class="text-[10px] text-slate-500 uppercase tracking-wider leading-none mb-0.5">{{ t('header.revPerDay') }}</div>
          <div class="text-lg font-bold text-sky-300 font-mono leading-none">{{ fmtRub(dailyRevenueRate) }}</div>
        </div>
        <div>
          <div class="text-[10px] text-slate-500 uppercase tracking-wider leading-none mb-0.5">{{ t('header.deployed') }}</div>
          <div class="text-lg font-bold text-slate-300 font-mono leading-none">{{ deployedCount }}</div>
        </div>
      </div>

      <div class="flex-1"></div>

      <div v-if="store.game" class="flex items-center gap-2 text-xs flex-shrink-0">
        <span class="text-slate-600 text-[10px] uppercase tracking-wider mr-1">WIP</span>
        <span
          v-for="col in wipCols"
          :key="col.key"
          :class="['flex items-center gap-1 px-2 py-1 rounded-md font-mono font-semibold', col.cls]"
        >
          <span class="text-[10px]">{{ col.icon }}</span>
          {{ col.count }}/{{ col.limit }}
        </span>
      </div>

      <div v-if="store.game" class="h-5 w-px bg-slate-700 flex-shrink-0"></div>

      <div v-if="store.game" class="flex items-center gap-2 flex-shrink-0">
        <span v-if="store.error" class="text-red-400 text-xs max-w-[200px] truncate">{{ store.error }}</span>

        <button @click="$emit('open-metrics')" class="btn-secondary text-sm py-2 px-4">
          📊 {{ t('metrics.title') }}
        </button>

        <button
          v-if="store.game.work_done && store.game.phase !== 'completed'"
          @click="store.endDay()"
          :disabled="store.loading"
          class="btn-success text-sm py-2 px-5"
        >
          {{ t('game.endDay') }}
        </button>

        <span :class="['px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider', phaseBadgeClass]">
          {{ phaseLabel }}
        </span>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'

defineEmits(['open-metrics'])
const { t } = useI18n()
const store = useGameStore()

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}

const progress = computed(() => {
  if (!store.game) return 0
  return ((store.game.current_day - 9) / (store.game.total_days - 9)) * 100
})

const deployedCount = computed(() =>
  store.game?.cards.filter(c => ['deployed', 'exp_deployed'].includes(c.column)).length || 0
)

const dailyRevenueRate = computed(() => {
  const deployed = store.game?.cards.filter(
    c => ['deployed', 'exp_deployed'].includes(c.column) && c.card_type === 'standard'
  ) || []
  return deployed.reduce((s, c) => s + (c.val || c.revenue_per_day || 0), 0)
})

const phaseLabel = computed(() => {
  if (store.game?.phase === 'completed') return t('phase.completed')
  if (store.game?.work_done) return t('phase.endDay')
  return t('phase.planning')
})

const wipCols = computed(() => {
  if (!store.game) return []
  const w = store.game.wip_limits
  const c = store.wipCounts
  return [
    { key: 'ready', icon: 'R', count: c.ready, limit: w.ready, cls: wipCls(c.ready, w.ready) },
    { key: 'analysis', icon: 'A', count: c.analysis, limit: w.analysis, cls: wipCls(c.analysis, w.analysis) },
    { key: 'development', icon: 'D', count: c.development, limit: w.development, cls: wipCls(c.development, w.development) },
    { key: 'test', icon: 'T', count: c.test, limit: w.test, cls: wipCls(c.test, w.test) },
  ]
})

function wipCls(count, limit) {
  if (count >= limit) return 'bg-red-950/60 text-red-400 border border-red-800/50'
  if (count >= limit - 1) return 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
  return 'bg-slate-800/60 text-slate-400 border border-slate-700/40'
}

const phaseBadgeClass = computed(() => {
  if (store.game?.phase === 'completed') return 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
  if (store.game?.work_done) return 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
  return 'bg-violet-950/60 text-violet-400 border border-violet-800/50'
})
</script>
