<template>
  <div class="min-h-screen bg-board-bg relative overflow-hidden flex flex-col">
    <!-- Decorative background glow -->
    <div class="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div class="absolute -top-32 -left-32 w-96 h-96 bg-amber-500/20 rounded-full blur-3xl"></div>
      <div class="absolute top-1/4 -right-32 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl"></div>
      <div class="absolute bottom-0 left-1/3 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"></div>
    </div>

    <div class="fixed top-4 right-4 z-50">
      <LanguageSelector />
    </div>

    <div class="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <!-- Title -->
      <div class="text-center mb-10 animate-fade-in">
        <div class="text-5xl mb-3">🏆</div>
        <h1 class="font-display text-4xl font-extrabold tracking-tight text-white mb-2">
          {{ t('leaderboard.title') }}
        </h1>
        <p class="text-slate-400 max-w-md mx-auto">{{ t('leaderboard.subtitle') }}</p>
      </div>

      <!-- Leaderboard card -->
      <div class="glass rounded-2xl p-6 sm:p-8 w-full max-w-xl animate-slide-up">
        <div v-if="loading" class="text-center text-slate-400 py-10">
          {{ t('leaderboard.loading') }}
        </div>

        <div v-else-if="error" class="text-center text-red-400 py-10">
          {{ t('leaderboard.error') }}
        </div>

        <div v-else-if="!entries.length" class="text-center text-slate-400 py-10">
          {{ t('leaderboard.empty') }}
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="(entry, i) in entries"
            :key="i"
            :class="[
              'flex items-center gap-4 rounded-xl px-4 py-3 transition-colors',
              i === 0 ? 'bg-gradient-to-r from-amber-500/15 to-transparent border border-amber-500/30' : 'bg-slate-800/50',
            ]"
          >
            <div :class="['w-10 text-center text-2xl font-display font-bold', rankColor(i)]">
              {{ rankIcon(i) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-white truncate">{{ entry.name }}</div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-emerald-400 font-mono font-bold">{{ fmtRub(entry.profit) }}</div>
            </div>
          </div>
        </div>
      </div>

      <button
        @click="$router.push('/')"
        class="mt-8 text-sm text-slate-400 hover:text-slate-200 transition-colors"
      >
        {{ t('leaderboard.backHome') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { leaderboardApi } from '../services/api.js'
import LanguageSelector from '../components/LanguageSelector.vue'

const { t } = useI18n()

const entries = ref([])
const loading = ref(true)
const error = ref(false)

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}

function rankIcon(i) {
  return ['🥇', '🥈', '🥉'][i] || `#${i + 1}`
}

function rankColor(i) {
  return ['text-yellow-400', 'text-slate-300', 'text-amber-600'][i] || 'text-slate-500'
}

async function loadLeaderboard() {
  loading.value = true
  error.value = false
  try {
    const res = await leaderboardApi.top()
    entries.value = res.data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadLeaderboard)
</script>
