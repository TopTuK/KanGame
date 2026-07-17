<template>
  <div class="min-h-screen bg-board-bg relative overflow-hidden flex flex-col">
    <!-- Decorative background glow -->
    <div class="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div class="absolute -top-32 -left-32 w-96 h-96 bg-sky-500/20 rounded-full blur-3xl"></div>
      <div class="absolute top-1/4 -right-32 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl"></div>
      <div class="absolute bottom-0 left-1/3 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"></div>
    </div>

    <div class="fixed top-4 right-4 z-50">
      <LanguageSelector />
    </div>

    <!-- Hero -->
    <div class="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <!-- Logo / Title -->
      <div class="text-center mb-12 animate-fade-in">
        <div class="flex items-center justify-center gap-3 mb-4">
          <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-sky-400 to-sky-600 flex items-center justify-center text-2xl font-display font-bold shadow-lg shadow-sky-500/30">K</div>
          <h1 class="font-display text-5xl font-extrabold tracking-tight text-white">
            Kan<span class="bg-gradient-to-r from-sky-400 to-sky-300 bg-clip-text text-transparent">Game</span>
          </h1>
        </div>
        <p class="text-xl text-slate-400 max-w-lg mx-auto mt-4">
          {{ t('home.tagline') }}
        </p>
      </div>

      <!-- Features row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl w-full mb-12 animate-slide-up">
        <div class="glass glass-hover rounded-2xl p-6 text-center">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-sky-500/10 flex items-center justify-center text-2xl">🎯</div>
          <h3 class="font-display font-semibold text-white mb-1">{{ t('home.pullSystem') }}</h3>
          <p class="text-sm text-slate-400">{{ t('home.pullSystemDesc') }}</p>
        </div>
        <div class="glass glass-hover rounded-2xl p-6 text-center">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-amber-500/10 flex items-center justify-center text-2xl">⚡</div>
          <h3 class="font-display font-semibold text-white mb-1">{{ t('home.classesOfService') }}</h3>
          <p class="text-sm text-slate-400">{{ t('home.classesOfServiceDesc') }}</p>
        </div>
        <div class="glass glass-hover rounded-2xl p-6 text-center">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-emerald-500/10 flex items-center justify-center text-2xl">📊</div>
          <h3 class="font-display font-semibold text-white mb-1">{{ t('home.realMetrics') }}</h3>
          <p class="text-sm text-slate-400">{{ t('home.realMetricsDesc') }}</p>
        </div>
      </div>

      <!-- New Game form (authenticated) -->
      <div v-if="authStore.isAuthenticated" class="glass rounded-2xl p-8 w-full max-w-md animate-slide-up">
        <div class="mb-4 text-sm">
          <div v-if="!editingUsername" class="flex items-center gap-2 text-slate-400">
            <span>{{ t('home.signedInAs', { username: authStore.user?.username }) }}</span>
            <button
              type="button"
              @click="startEditUsername"
              class="text-sky-400 hover:text-sky-300 transition-colors"
              :aria-label="t('home.editUsername')"
            >✎</button>
          </div>
          <form v-else @submit.prevent="saveUsername" class="flex items-center gap-2">
            <input
              v-model="usernameDraft"
              type="text"
              maxlength="255"
              required
              class="flex-1 px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-sky-500"
            />
            <button type="submit" :disabled="savingUsername" class="text-emerald-400 hover:text-emerald-300 text-sm font-medium">
              {{ t('home.usernameSave') }}
            </button>
            <button type="button" @click="editingUsername = false" class="text-slate-400 hover:text-slate-200 text-sm">
              {{ t('home.usernameCancel') }}
            </button>
          </form>
        </div>
        <div class="flex items-center justify-between mb-6">
          <h2 class="font-display text-2xl font-bold text-white text-center flex-1">{{ t('home.startNewGame') }}</h2>
        </div>
        <button
          @click="startGame"
          :disabled="creating"
          class="w-full btn-primary text-lg py-3 rounded-xl mt-2"
        >
          <span v-if="creating">{{ t('home.creating') }}</span>
          <span v-else>{{ t('home.startGame') }}</span>
        </button>
        <button
          @click="authStore.logout()"
          class="w-full mt-4 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          {{ t('home.signOut') }}
        </button>
      </div>

      <!-- Sign in CTA (unauthenticated) -->
      <div v-else-if="authStore.checked" class="glass rounded-2xl p-8 w-full max-w-md animate-slide-up text-center">
        <h2 class="font-display text-2xl font-bold text-white mb-4">{{ t('home.signInPrompt') }}</h2>
        <p class="text-sm text-slate-400 mb-6">{{ t('home.signInPromptDesc') }}</p>
        <button @click="signIn" class="w-full btn-primary text-lg py-3 rounded-xl">
          {{ t('home.signIn') }}
        </button>
        <router-link to="/demo" class="block w-full mt-4 text-sm text-slate-400 hover:text-slate-200 transition-colors">
          {{ t('home.tryDemo') }}
        </router-link>
      </div>

      <!-- Existing games -->
      <div v-if="authStore.isAuthenticated && games.length" class="mt-12 w-full max-w-2xl animate-fade-in">
        <h3 class="font-display text-lg font-semibold text-slate-300 mb-4">{{ t('home.recentGames') }}</h3>
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

    <!-- External links -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl w-full mx-auto mt-12 mb-4 animate-fade-in px-4">
      <router-link
        to="/leaderboard"
        class="glass glass-hover rounded-2xl p-6 flex flex-col items-center text-center"
      >
        <div class="w-12 h-12 mb-3 rounded-xl bg-amber-500/10 flex items-center justify-center text-2xl">🏆</div>
        <h3 class="font-display font-semibold text-white mb-1">{{ t('home.leaderboardLink') }}</h3>
        <p class="text-sm text-slate-400">{{ t('home.leaderboardLinkDesc') }}</p>
      </router-link>
      <a
        href="https://s-sidorov.ru"
        target="_blank"
        rel="noopener noreferrer"
        class="glass glass-hover rounded-2xl p-6 flex flex-col items-center text-center"
      >
        <div class="w-12 h-12 mb-3 rounded-xl bg-sky-500/10 flex items-center justify-center text-2xl">🌐</div>
        <h3 class="font-display font-semibold text-white mb-1">{{ t('home.authorLink') }}</h3>
        <p class="text-sm text-slate-400">{{ t('home.authorLinkDesc') }}</p>
      </a>
      <a
        href="https://pmi.moscow"
        target="_blank"
        rel="noopener noreferrer"
        class="glass glass-hover rounded-2xl p-6 flex flex-col items-center text-center"
      >
        <div class="w-12 h-12 mb-3 rounded-xl bg-amber-500/10 flex items-center justify-center text-2xl">🤝</div>
        <h3 class="font-display font-semibold text-white mb-1">{{ t('home.communityLink') }}</h3>
        <p class="text-sm text-slate-400">{{ t('home.communityLinkDesc') }}</p>
      </a>
    </div>

    <!-- Footer -->
    <footer class="relative text-center py-4 text-slate-600 text-sm border-t border-white/5">
      {{ t('home.footer') }}
    </footer>

    <DesktopOnlyModal v-if="showDesktopOnlyModal" @close="showDesktopOnlyModal = false" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { gamesApi } from '../services/api.js'
import { useGameContent } from '../composables/useGameContent.js'
import { useAuthStore } from '../stores/authStore.js'
import { useIsMobileOrTablet } from '../composables/useIsMobileOrTablet.js'
import LanguageSelector from '../components/LanguageSelector.vue'
import DesktopOnlyModal from '../components/DesktopOnlyModal.vue'

const { t } = useI18n()
const { statusLabel } = useGameContent()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { isMobileOrTablet } = useIsMobileOrTablet()

const showDesktopOnlyModal = ref(false)
if (route.query.blocked) {
  showDesktopOnlyModal.value = true
  router.replace({ path: '/' })
}

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}
const creating = ref(false)
const games = ref([])
const editingUsername = ref(false)
const usernameDraft = ref('')
const savingUsername = ref(false)

function signIn() {
  window.location.href = 'https://localhost:8000/auth/login'
}

async function loadGames() {
  try {
    const res = await gamesApi.list()
    games.value = res.data
  } catch {}
}

function startEditUsername() {
  usernameDraft.value = authStore.user?.username || ''
  editingUsername.value = true
}

async function saveUsername() {
  savingUsername.value = true
  try {
    await authStore.updateUsername(usernameDraft.value.trim())
    editingUsername.value = false
  } finally {
    savingUsername.value = false
  }
}

watch(
  () => authStore.checked,
  (checked) => {
    if (checked && authStore.isAuthenticated) {
      loadGames()
    }
  },
  { immediate: true }
)

async function startGame() {
  if (isMobileOrTablet.value) {
    showDesktopOnlyModal.value = true
    return
  }
  creating.value = true
  try {
    const res = await gamesApi.create({
      player_name: authStore.user?.username || '',
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
