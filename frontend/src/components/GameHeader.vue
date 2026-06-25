<template>
  <header class="bg-slate-900 border-b border-slate-700/50 px-6 py-3 flex items-center justify-between flex-shrink-0">
    <!-- Left: logo + game info -->
    <div class="flex items-center gap-4">
      <router-link to="/" class="flex items-center gap-2 hover:opacity-80 transition-opacity">
        <div class="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center font-bold text-sm">K</div>
        <span class="text-white font-bold text-lg">KanGame</span>
      </router-link>

      <div v-if="store.game" class="flex items-center gap-3 ml-2 text-sm">
        <div class="text-slate-400">·</div>
        <div class="text-white font-medium">{{ store.game.name }}</div>
        <div class="text-slate-400">·</div>
        <div class="text-slate-300">{{ store.game.player_name }}</div>
      </div>
    </div>

    <!-- Center: Day progress -->
    <div v-if="store.game" class="flex items-center gap-4">
      <div class="text-center">
        <div class="text-xs text-slate-500 uppercase tracking-wider">{{ t('header.day') }}</div>
        <div class="text-2xl font-bold font-mono text-sky-400">
          {{ store.game.current_day }}<span class="text-slate-600 text-lg">/{{ store.game.total_days }}</span>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="w-32">
        <div class="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            class="h-full bg-sky-500 rounded-full transition-all duration-500"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <div class="text-xs text-slate-500 mt-1 text-center">{{ t('header.complete', { percent: Math.round(progress) }) }}</div>
      </div>
    </div>

    <!-- Right: Revenue + status -->
    <div v-if="store.game" class="flex items-center gap-6">
      <!-- Revenue -->
      <div class="text-right">
        <div class="text-xs text-slate-500 uppercase tracking-wider">{{ t('header.totalRevenue') }}</div>
        <div class="text-xl font-bold text-emerald-400 font-mono">${{ store.game.total_revenue.toLocaleString() }}</div>
      </div>

      <!-- Deployed count -->
      <div class="text-right">
        <div class="text-xs text-slate-500 uppercase tracking-wider">{{ t('header.deployed') }}</div>
        <div class="text-xl font-bold text-sky-400 font-mono">{{ deployedCount }}</div>
      </div>

      <!-- Status badge -->
      <div :class="['px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider', statusClass]">
        {{ statusLabel(store.game.status) }}
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import { useGameContent } from '../composables/useGameContent.js'

const { t } = useI18n()
const { statusLabel } = useGameContent()
const store = useGameStore()

const progress = computed(() => {
  if (!store.game) return 0
  return ((store.game.current_day - 1) / store.game.total_days) * 100
})

const deployedCount = computed(() =>
  store.game?.cards.filter(c => c.column === 'deployed').length || 0
)

const statusClass = computed(() => {
  const s = store.game?.status
  if (s === 'active') return 'bg-sky-900/60 text-sky-300 border border-sky-700'
  if (s === 'completed') return 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
  return 'bg-slate-700 text-slate-300'
})
</script>
