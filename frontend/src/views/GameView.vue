<template>
  <div class="h-screen flex flex-col overflow-hidden bg-board-bg">
    <GameHeader @open-metrics="showMetrics = true" @open-analytics="showAnalytics = true" />

    <div v-if="store.loading && !store.game" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-400">{{ t('game.loading') }}</p>
      </div>
    </div>

    <template v-else-if="store.game">
      <HelpModal v-if="showHelp" @close="showHelp = false" />
      <MetricsModal v-if="showMetrics" @close="showMetrics = false" />
      <AnalyticsModal v-if="showAnalytics" @close="showAnalytics = false" />
      <WorkLogModal v-if="store.showWorkLog" :log="store.workLog" @close="store.dismissWorkLog()" />
      <EndDayModal v-if="store.endDayModal" :modal="store.endDayModal" @close="store.dismissEndDayModal()" />
      <ScoreModal v-if="store.isGameOver" @view-analytics="showAnalytics = true" />

      <div class="border-b border-slate-700/50 bg-slate-900/80 flex-shrink-0">
        <ResourcePanel />
      </div>

      <div
        ref="boardScrollEl"
        class="flex-1 overflow-x-auto overflow-y-auto p-3"
        @dragover="onBoardDragOver"
        @dragleave="onBoardDragLeave"
      >
        <KanbanBoard />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import GameHeader from '../components/GameHeader.vue'
import KanbanBoard from '../components/KanbanBoard.vue'
import ResourcePanel from '../components/ResourcePanel.vue'
import MetricsModal from '../components/MetricsModal.vue'
import AnalyticsModal from '../components/AnalyticsModal.vue'
import ScoreModal from '../components/ScoreModal.vue'
import HelpModal from '../components/HelpModal.vue'
import WorkLogModal from '../components/WorkLogModal.vue'
import EndDayModal from '../components/EndDayModal.vue'

const { t } = useI18n()
const route = useRoute()
const store = useGameStore()
const showHelp = ref(false)
const showMetrics = ref(false)
const showAnalytics = ref(false)

// Native HTML5 drag-and-drop suppresses normal wheel scrolling for its
// duration, and this layout has no page-level scroll fallback (h-screen
// overflow-hidden), so without this a worker can't be dragged to a card
// below the fold. Auto-scroll the board while dragging near its edges.
const boardScrollEl = ref(null)
const DRAG_SCROLL_EDGE = 60
const DRAG_SCROLL_SPEED = 14
let dragPointerY = null
let dragScrollRafId = null

function dragScrollLoop() {
  const el = boardScrollEl.value
  if (el && dragPointerY != null) {
    const rect = el.getBoundingClientRect()
    if (dragPointerY < rect.top + DRAG_SCROLL_EDGE) {
      const intensity = (rect.top + DRAG_SCROLL_EDGE - dragPointerY) / DRAG_SCROLL_EDGE
      el.scrollTop -= DRAG_SCROLL_SPEED * intensity
    } else if (dragPointerY > rect.bottom - DRAG_SCROLL_EDGE) {
      const intensity = (dragPointerY - (rect.bottom - DRAG_SCROLL_EDGE)) / DRAG_SCROLL_EDGE
      el.scrollTop += DRAG_SCROLL_SPEED * intensity
    }
  }
  dragScrollRafId = requestAnimationFrame(dragScrollLoop)
}

function onBoardDragOver(event) {
  dragPointerY = event.clientY
}

function onBoardDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    dragPointerY = null
  }
}

function stopDragScroll() {
  dragPointerY = null
}

onMounted(async () => {
  await store.loadGame(route.params.id)
  if (store.game?.current_day === 9 && !store.game?.metrics?.length) {
    showHelp.value = true
  }
  dragScrollRafId = requestAnimationFrame(dragScrollLoop)
  window.addEventListener('dragend', stopDragScroll)
  window.addEventListener('drop', stopDragScroll)
})

onBeforeUnmount(() => {
  if (dragScrollRafId) cancelAnimationFrame(dragScrollRafId)
  window.removeEventListener('dragend', stopDragScroll)
  window.removeEventListener('drop', stopDragScroll)
})
</script>
