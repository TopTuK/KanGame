<template>
  <div class="flex flex-col gap-3 min-h-full min-w-max pb-2">
    <!-- Expedite track -->
    <div class="flex items-start gap-2">
      <!--<div class="flex-shrink-0 w-16 flex items-center justify-center">
        <span class="text-xs font-bold text-red-400 uppercase tracking-wider -rotate-90 whitespace-nowrap">
          {{ t('board.expediteTrack') }}
        </span>
      </div>-->
      <KanbanColumn
        v-for="col in expediteColumns"
        :key="col.key"
        :column="col"
        :cards="store.cardsByColumn[col.key] || []"
        :wip-count="col.wipCount"
      />
    </div>

    <!-- Standard track -->
    <div class="flex items-start gap-2 border-t border-red-900/40 pt-3">
      <KanbanColumn
        v-for="col in standardColumns"
        :key="col.key"
        :column="col"
        :cards="store.cardsByColumn[col.key] || []"
        :wip-count="col.wipCount"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import KanbanColumn from './KanbanColumn.vue'

const { t } = useI18n()
const store = useGameStore()

const wip = computed(() => store.game?.wip_limits || {})
const counts = computed(() => store.wipCounts)

function colDef(key, labelKey, icon, color, wipKey, wipLimit) {
  return {
    key,
    label: t(`columns.${labelKey}.label`),
    description: t(`columns.${labelKey}.description`, { limit: wipLimit ?? '' }),
    icon,
    color,
    wipLimit: wipLimit ?? null,
    wipCount: wipKey ? counts.value[wipKey] : null,
    pullable: store.isPullableColumn(key),
  }
}

const standardColumns = computed(() => [
  colDef('backlog', 'backlog', '📋', 'slate', null, null),
  colDef('ready', 'ready', '✅', 'slate', 'ready', wip.value.ready),
  colDef('analysis', 'analysis', '🔍', 'violet', 'analysis', wip.value.analysis),
  colDef('analysis_done', 'analysisDone', '✓', 'violet', null, null),
  colDef('development', 'development', '💻', 'sky', 'development', wip.value.development),
  colDef('dev_done', 'devDone', '✓', 'sky', null, null),
  colDef('test', 'test', '🧪', 'amber', 'test', wip.value.test),
  colDef('deployed', 'deployed', '🚀', 'emerald', null, null),
])

const expediteColumns = computed(() => [
  colDef('exp_backlog', 'expBacklog', '⚡', 'red', null, null),
  colDef('exp_ready', 'expReady', '⚡', 'red', 'expedite', wip.value.expedite),
  colDef('exp_analysis', 'expAnalysis', '🔍', 'red', 'exp_analysis', wip.value.analysis),
  colDef('exp_analysis_done', 'expAnalysisDone', '✓', 'red', null, null),
  colDef('exp_development', 'expDevelopment', '💻', 'red', 'exp_development', wip.value.development),
  colDef('exp_dev_done', 'expDevDone', '✓', 'red', null, null),
  colDef('exp_test', 'expTest', '🧪', 'red', 'exp_test', wip.value.test),
  colDef('exp_deployed', 'expDeployed', '🚀', 'red', null, null),
])
</script>
