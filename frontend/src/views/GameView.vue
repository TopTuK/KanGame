<template>
  <div class="h-screen flex flex-col overflow-hidden bg-board-bg">
    <GameHeader />

    <div v-if="store.loading && !store.game" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-400">{{ t('game.loading') }}</p>
      </div>
    </div>

    <template v-else-if="store.game">
      <HelpModal v-if="showHelp" @close="showHelp = false" />
      <WorkLogModal v-if="store.showWorkLog" :log="store.workLog" @close="store.dismissWorkLog()" />
      <EndDayModal v-if="store.endDayModal" :modal="store.endDayModal" @close="store.dismissEndDayModal()" />
      <ScoreModal v-if="store.isGameOver" />

      <div class="border-b border-slate-700/50 bg-slate-900/80 flex-shrink-0">
        <ResourcePanel />
      </div>

      <div class="flex-1 flex overflow-hidden">
        <div class="flex-1 overflow-x-auto overflow-y-hidden p-3">
          <KanbanBoard />
        </div>
        <div class="w-64 border-l border-slate-700/50 overflow-y-auto flex-shrink-0">
          <MetricsPanel />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import GameHeader from '../components/GameHeader.vue'
import KanbanBoard from '../components/KanbanBoard.vue'
import ResourcePanel from '../components/ResourcePanel.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import ScoreModal from '../components/ScoreModal.vue'
import HelpModal from '../components/HelpModal.vue'
import WorkLogModal from '../components/WorkLogModal.vue'
import EndDayModal from '../components/EndDayModal.vue'

const { t } = useI18n()
const route = useRoute()
const store = useGameStore()
const showHelp = ref(false)

onMounted(async () => {
  await store.loadGame(route.params.id)
  if (store.game?.current_day === 9 && !store.game?.metrics?.length) {
    showHelp.value = true
  }
})
</script>
