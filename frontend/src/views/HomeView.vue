<template>
  <div class="min-h-screen bg-board-bg flex flex-col">
    <div class="fixed top-4 right-4 z-50">
      <LanguageSelector />
    </div>

    <!-- Hero -->
    <div class="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <!-- Logo / Title -->
      <div class="text-center mb-12 animate-fade-in">
        <div class="flex items-center justify-center gap-3 mb-4">
          <div class="w-12 h-12 rounded-xl bg-sky-500 flex items-center justify-center text-2xl font-bold">K</div>
          <h1 class="text-5xl font-extrabold tracking-tight text-white">
            Kan<span class="text-sky-400">Game</span>
          </h1>
        </div>
        <p class="text-xl text-slate-400 max-w-lg mx-auto mt-4">
          {{ t('home.tagline') }}
        </p>
      </div>

      <!-- Features row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl w-full mb-12 animate-slide-up">
        <div class="glass rounded-xl p-5 text-center">
          <div class="text-3xl mb-3">🎯</div>
          <h3 class="font-semibold text-white mb-1">{{ t('home.pullSystem') }}</h3>
          <p class="text-sm text-slate-400">{{ t('home.pullSystemDesc') }}</p>
        </div>
        <div class="glass rounded-xl p-5 text-center">
          <div class="text-3xl mb-3">⚡</div>
          <h3 class="font-semibold text-white mb-1">{{ t('home.classesOfService') }}</h3>
          <p class="text-sm text-slate-400">{{ t('home.classesOfServiceDesc') }}</p>
        </div>
        <div class="glass rounded-xl p-5 text-center">
          <div class="text-3xl mb-3">📊</div>
          <h3 class="font-semibold text-white mb-1">{{ t('home.realMetrics') }}</h3>
          <p class="text-sm text-slate-400">{{ t('home.realMetricsDesc') }}</p>
        </div>
      </div>

      <!-- New Game form -->
      <div class="glass rounded-2xl p-8 w-full max-w-md animate-slide-up">
        <h2 class="text-2xl font-bold text-white mb-6 text-center">{{ t('home.startNewGame') }}</h2>
        <form @submit.prevent="startGame" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">{{ t('home.yourName') }}</label>
            <input
              v-model="playerName"
              type="text"
              :placeholder="t('home.yourNamePlaceholder')"
              required
              class="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">{{ t('home.gameName') }}</label>
            <input
              v-model="gameName"
              type="text"
              :placeholder="t('home.gameNamePlaceholder')"
              required
              class="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            :disabled="creating"
            class="w-full btn-primary text-lg py-3 rounded-xl mt-2"
          >
            <span v-if="creating">{{ t('home.creating') }}</span>
            <span v-else>{{ t('home.startGame') }}</span>
          </button>
        </form>
      </div>

      <!-- Existing games -->
      <div v-if="games.length" class="mt-12 w-full max-w-2xl animate-fade-in">
        <h3 class="text-lg font-semibold text-slate-300 mb-4">{{ t('home.recentGames') }}</h3>
        <div class="space-y-3">
          <div
            v-for="g in games"
            :key="g.id"
            @click="$router.push(`/game/${g.id}`)"
            class="glass rounded-xl px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-white/10 transition-colors group"
          >
            <div>
              <div class="font-semibold text-white group-hover:text-sky-400 transition-colors">{{ g.name }}</div>
              <div class="text-sm text-slate-400">
                {{ g.player_name }} · {{ t('home.dayOf', { current: g.current_day, total: g.total_days }) }}
              </div>
            </div>
            <div class="text-right">
              <div class="text-emerald-400 font-mono font-bold">{{ fmtRub(g.total_revenue) }}</div>
              <div :class="['text-xs font-medium px-2 py-0.5 rounded-full mt-1', statusColor(g.status)]">
                {{ statusLabel(g.status) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="text-center py-4 text-slate-600 text-sm">
      {{ t('home.footer') }}
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { gamesApi } from '../services/api.js'
import { useGameContent } from '../composables/useGameContent.js'
import LanguageSelector from '../components/LanguageSelector.vue'

const { t } = useI18n()
const { statusLabel } = useGameContent()
const router = useRouter()

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}
const playerName = ref('')
const gameName = ref('')
const creating = ref(false)
const games = ref([])

onMounted(async () => {
  try {
    const res = await gamesApi.list()
    games.value = res.data
  } catch {}
})

async function startGame() {
  creating.value = true
  try {
    const res = await gamesApi.create({
      name: gameName.value,
      player_name: playerName.value,
    })
    router.push(`/game/${res.data.id}`)
  } finally {
    creating.value = false
  }
}

function statusColor(status) {
  if (status === 'active') return 'bg-sky-900 text-sky-300'
  if (status === 'completed') return 'bg-emerald-900 text-emerald-300'
  return 'bg-slate-700 text-slate-300'
}
</script>
