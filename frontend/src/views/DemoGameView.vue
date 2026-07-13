<template>
  <div class="h-screen flex flex-col overflow-hidden bg-board-bg">
    <template v-if="!store.game">
      <header class="flex-shrink-0 bg-slate-900 border-b border-slate-700/60 px-5 py-2.5">
        <router-link to="/" class="flex items-center gap-2 hover:opacity-80 transition-opacity w-fit">
          <div class="w-7 h-7 rounded-md bg-sky-500 flex items-center justify-center font-bold text-xs text-white">K</div>
          <span class="text-white font-bold text-base leading-none">KanGame</span>
        </router-link>
      </header>

      <div class="flex-1 flex items-center justify-center px-4">
        <div class="bg-slate-900 border border-slate-600 rounded-2xl max-w-lg w-full shadow-2xl">
          <div class="px-6 py-4 border-b border-slate-700">
            <h2 class="text-xl font-bold text-white">{{ t('demo.title') }}</h2>
          </div>
          <div class="px-6 py-5 text-sm text-slate-300 space-y-3 leading-relaxed">
            <p>{{ t('demo.intro') }}</p>
            <ul class="list-disc list-inside space-y-1 text-amber-300">
              <li>{{ t('demo.scopeWarning') }}</li>
              <li>{{ t('demo.saveWarning') }}</li>
              <li>{{ t('demo.resumeWarning') }}</li>
            </ul>
            <p v-if="store.error" class="text-red-400">{{ store.error }}</p>
          </div>
          <div class="px-6 py-4 border-t border-slate-700 flex justify-end">
            <button @click="store.startDemo()" :disabled="store.loading" class="btn-primary px-6 py-2">
              <span v-if="store.loading">{{ t('home.creating') }}</span>
              <span v-else>{{ t('demo.startButton') }}</span>
            </button>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <GameHeader @open-metrics="showMetrics = true" @open-analytics="showAnalytics = true" />
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
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import GameHeader from '../components/GameHeader.vue'
import KanbanBoard from '../components/KanbanBoard.vue'
import ResourcePanel from '../components/ResourcePanel.vue'
import MetricsModal from '../components/MetricsModal.vue'
import AnalyticsModal from '../components/AnalyticsModal.vue'
import ScoreModal from '../components/ScoreModal.vue'
import WorkLogModal from '../components/WorkLogModal.vue'
import EndDayModal from '../components/EndDayModal.vue'

const { t } = useI18n()
const store = useGameStore()
const showMetrics = ref(false)
const showAnalytics = ref(false)

// Mirrors GameView.vue's drag-scroll behavior (see there for rationale).
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

onMounted(() => {
  // A demo is never resumable: always land back on the warning/intro
  // screen, even if a previous demo (or real game) is still in the store.
  store.resetGame()
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
