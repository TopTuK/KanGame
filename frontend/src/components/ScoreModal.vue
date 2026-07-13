<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div class="glass rounded-2xl max-w-2xl w-full shadow-2xl border border-emerald-600/30 animate-slide-up overflow-hidden">
        <!-- Header -->
        <div class="bg-gradient-to-r from-emerald-900 to-sky-900 px-8 py-6 text-center">
          <div class="text-5xl mb-3">🏁</div>
          <h2 class="text-3xl font-extrabold text-white mb-1">{{ t('score.gameComplete') }}</h2>
          <p class="text-slate-300">{{ store.game?.player_name }} — {{ store.game?.name }}</p>
        </div>

        <!-- Score -->
        <div class="px-8 py-6">
          <div class="text-center mb-8">
            <div class="text-slate-400 text-sm uppercase tracking-wider mb-1">{{ t('score.totalRevenue') }}</div>
            <div class="text-6xl font-extrabold font-mono text-emerald-400 mb-2">
              {{ fmtRub(store.game?.total_revenue) }}
            </div>
            <div :class="['text-xl font-bold', rankColor]">{{ rank }}</div>
          </div>

          <!-- Stats grid -->
          <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="text-center bg-slate-800/60 rounded-xl p-4">
              <div class="text-3xl font-bold text-sky-400 font-mono">{{ deployedCount }}</div>
              <div class="text-xs text-slate-400 mt-1">{{ t('score.featuresDeployed') }}</div>
            </div>
            <div class="text-center bg-slate-800/60 rounded-xl p-4">
              <div class="text-3xl font-bold text-amber-400 font-mono">{{ totalWip }}</div>
              <div class="text-xs text-slate-400 mt-1">{{ t('score.cardsInProgress') }}</div>
            </div>
            <div class="text-center bg-slate-800/60 rounded-xl p-4">
              <div class="text-3xl font-bold text-violet-400 font-mono">{{ avgThroughput }}</div>
              <div class="text-xs text-slate-400 mt-1">{{ t('score.avgThroughput') }}</div>
            </div>
          </div>

          <!-- Revenue chart (simple bars) -->
          <div class="bg-slate-800/40 rounded-xl p-4 mb-6">
            <div class="text-xs text-slate-400 uppercase tracking-wider mb-3">{{ t('score.dailyRevenue') }}</div>
            <div class="flex items-end gap-0.5 h-16">
              <div
                v-for="m in metrics"
                :key="m.day"
                class="flex-1 bg-emerald-500/70 rounded-t hover:bg-emerald-400 transition-colors"
                :style="{ height: (m.daily_revenue / maxRevenue * 100) + '%' }"
                :title="t('score.dayTooltip', { day: m.day, amount: fmtRub(m.daily_revenue) })"
              ></div>
            </div>
            <div class="flex justify-between text-xs text-slate-600 mt-1">
              <span>{{ t('score.dayLabel', { day: firstDay }) }}</span>
              <span>{{ t('score.dayLabel', { day: lastDay }) }}</span>
            </div>
          </div>

          <div class="flex gap-3 justify-center">
            <button @click="$router.push('/')" class="btn-secondary">
              {{ t('score.backHome') }}
            </button>
            <button @click="newGame" class="btn-primary">
              {{ store.game?.is_demo ? t('demo.playAgain') : t('score.newGame') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import { gamesApi } from '../services/api.js'

const { t } = useI18n()
const store = useGameStore()
const router = useRouter()

const metrics = computed(() => store.game?.metrics || [])
const cards = computed(() => store.game?.cards || [])
const firstDay = computed(() => metrics.value[0]?.day ?? 9)
const lastDay = computed(() => metrics.value[metrics.value.length - 1]?.day ?? store.game?.total_days ?? 35)

const deployedCount = computed(() =>
  cards.value.filter(c => ['deployed', 'exp_deployed'].includes(c.column)).length
)
const totalWip = computed(() =>
  cards.value.filter(c =>
    ['analysis', 'analysis_done', 'development', 'dev_done', 'test', 'test_done'].includes(c.column)
  ).length
)
const avgThroughput = computed(() => {
  if (!metrics.value.length) return 0
  const total = metrics.value.reduce((s, m) => s + m.throughput, 0)
  return (total / metrics.value.length).toFixed(1)
})
const maxRevenue = computed(() => Math.max(1, ...metrics.value.map(m => m.daily_revenue)))

const rank = computed(() => {
  const rev = store.game?.total_revenue || 0
  if (rev >= 700000) return t('score.rankMaster')
  if (rev >= 500000) return t('score.rankExpert')
  if (rev >= 300000) return t('score.rankPractitioner')
  if (rev >= 150000) return t('score.rankStarter')
  return t('score.rankLearning')
})

const rankColor = computed(() => {
  const rev = store.game?.total_revenue || 0
  if (rev >= 700000) return 'text-yellow-400'
  if (rev >= 500000) return 'text-yellow-300'
  if (rev >= 300000) return 'text-slate-300'
  if (rev >= 150000) return 'text-amber-600'
  return 'text-slate-500'
})

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}

async function newGame() {
  const game = store.game
  if (!game) return
  if (game.is_demo) {
    await store.startDemo()
    return
  }
  const res = await gamesApi.create({ name: game.name + ' (2)', player_name: game.player_name })
  router.push(`/game/${res.data.id}`)
}
</script>
