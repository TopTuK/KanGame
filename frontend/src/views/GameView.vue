<template>
  <div class="h-screen flex flex-col overflow-hidden bg-board-bg">
    <!-- Header -->
    <GameHeader />

    <!-- Loading -->
    <div v-if="store.loading && !store.game" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-400">{{ t('game.loading') }}</p>
      </div>
    </div>

    <!-- Game content -->
    <template v-else-if="store.game">
      <!-- Event modal -->
      <EventModal v-if="showEventModal" />

      <!-- Score modal -->
      <ScoreModal v-if="store.isGameOver" />

      <!-- Top resource strip -->
      <div class="border-b border-slate-700/50 bg-slate-900/80 flex-shrink-0">
        <ResourcePanel />
      </div>

      <!-- Main layout: board + metrics sidebar -->
      <div class="flex-1 flex overflow-hidden">
        <!-- Kanban Board (scrollable horizontally) -->
        <div class="flex-1 overflow-x-auto overflow-y-hidden p-4">
          <KanbanBoard />
        </div>

        <!-- Right sidebar -->
        <div class="w-80 border-l border-slate-700/50 overflow-y-auto flex-shrink-0">
          <MetricsPanel />
        </div>
      </div>

      <!-- Bottom action bar -->
      <div class="border-t border-slate-700/50 px-6 py-3 flex items-center justify-between bg-slate-900/80">
        <div class="flex items-center gap-3 text-sm text-slate-400">
          <span>{{ t('game.phase') }}: <span class="text-sky-400 font-medium capitalize">{{ phaseLabel(store.game.phase) }}</span></span>
          <span>·</span>
          <span>
            {{ t('game.wipAnalysis') }}:
            <span :class="wipClass('analysis')">{{ store.wipCounts.analysis }}/{{ store.game.wip_limits.analysis }}</span>
            · {{ t('game.wipDev') }}:
            <span :class="wipClass('development')">{{ store.wipCounts.development }}/{{ store.game.wip_limits.development }}</span>
            · {{ t('game.wipTest') }}:
            <span :class="wipClass('test')">{{ store.wipCounts.test }}/{{ store.game.wip_limits.test }}</span>
          </span>
        </div>

        <div class="flex items-center gap-3">
          <span v-if="translatedError" class="text-red-400 text-sm max-w-xs truncate">{{ translatedError }}</span>

          <!-- Phase buttons -->
          <button
            v-if="store.game.phase === 'event'"
            @click="store.resolveEvent()"
            :disabled="store.loading"
            class="btn-primary"
          >
            {{ todayEventTitle ? t('game.readEvent') : t('game.startDay') }}
          </button>

          <button
            v-if="store.game.phase === 'capacity' || store.game.phase === 'move'"
            @click="store.endDay()"
            :disabled="store.loading"
            class="btn-success"
          >
            {{ t('game.endDay') }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import { useGameContent } from '../composables/useGameContent.js'
import GameHeader from '../components/GameHeader.vue'
import KanbanBoard from '../components/KanbanBoard.vue'
import ResourcePanel from '../components/ResourcePanel.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import EventModal from '../components/EventModal.vue'
import ScoreModal from '../components/ScoreModal.vue'

const { t } = useI18n()
const { phaseLabel, eventTitle, translateError } = useGameContent()
const route = useRoute()
const store = useGameStore()

onMounted(() => store.loadGame(route.params.id))

const showEventModal = computed(() =>
  store.game?.phase === 'event' && store.todayEvent !== null
)

const todayEventTitle = computed(() => {
  const event = store.todayEvent
  return event ? eventTitle(event) : null
})

const translatedError = computed(() => translateError(store.error))

function wipClass(col) {
  const count = store.wipCounts[col] || 0
  const limit = store.game?.wip_limits[col] || 999
  if (count >= limit) return 'text-red-400 font-bold'
  if (count >= limit - 1) return 'text-yellow-400 font-semibold'
  return 'text-emerald-400 font-semibold'
}
</script>
