<template>
  <div class="flex flex-col gap-3 min-h-full min-w-max pb-2">
    <!-- Expedite track -->
    <div class="flex items-start gap-2">
      <template v-for="item in expediteItems" :key="item.type === 'single' ? item.col.key : item.active.key">
        <KanbanColumn
          v-if="item.type === 'single'"
          :column="item.col"
          :cards="store.cardsByColumn[item.col.key] || []"
          :wip-count="item.col.wipCount"
        />
        <KanbanColumnGroup
          v-else
          :title="item.title"
          :active-column="item.active"
          :done-column="item.done"
          :active-cards="store.cardsByColumn[item.active.key] || []"
          :done-cards="store.cardsByColumn[item.done.key] || []"
          :wip-limit="item.wipLimit"
          :wip-count="item.wipCount"
        />
      </template>
    </div>

    <!-- Standard track -->
    <div class="flex items-start gap-2 border-t border-red-900/40 pt-3">
      <template v-for="item in standardItems" :key="item.type === 'single' ? item.col.key : item.active.key">
        <KanbanColumn
          v-if="item.type === 'single'"
          :column="item.col"
          :cards="store.cardsByColumn[item.col.key] || []"
          :wip-count="item.col.wipCount"
        />
        <KanbanColumnGroup
          v-else
          :title="item.title"
          :active-column="item.active"
          :done-column="item.done"
          :active-cards="store.cardsByColumn[item.active.key] || []"
          :done-cards="store.cardsByColumn[item.done.key] || []"
          :wip-limit="item.wipLimit"
          :wip-count="item.wipCount"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import KanbanColumn from './KanbanColumn.vue'
import KanbanColumnGroup from './KanbanColumnGroup.vue'

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

const standardCols = computed(() => ({
  backlog: colDef('backlog', 'backlog', '📋', 'slate', null, null),
  ready: colDef('ready', 'ready', '✅', 'slate', 'ready', wip.value.ready),
  analysis: colDef('analysis', 'analysis', '🔍', 'violet', null, null),
  analysis_done: colDef('analysis_done', 'analysisDone', '✓', 'violet', null, null),
  development: colDef('development', 'development', '💻', 'sky', null, null),
  dev_done: colDef('dev_done', 'devDone', '✓', 'sky', null, null),
  test: colDef('test', 'test', '🧪', 'amber', null, null),
  test_done: colDef('test_done', 'testDone', '✓', 'amber', null, null),
  deployed: colDef('deployed', 'deployed', '🚀', 'emerald', null, null),
}))

const expediteCols = computed(() => ({
  exp_backlog: colDef('exp_backlog', 'expBacklog', '⚡', 'red', null, null),
  exp_ready: colDef('exp_ready', 'expReady', '⚡', 'red', 'expedite', wip.value.expedite),
  exp_analysis: colDef('exp_analysis', 'expAnalysis', '🔍', 'red', null, null),
  exp_analysis_done: colDef('exp_analysis_done', 'expAnalysisDone', '✓', 'red', null, null),
  exp_development: colDef('exp_development', 'expDevelopment', '💻', 'red', null, null),
  exp_dev_done: colDef('exp_dev_done', 'expDevDone', '✓', 'red', null, null),
  exp_test: colDef('exp_test', 'expTest', '🧪', 'red', null, null),
  exp_test_done: colDef('exp_test_done', 'expTestDone', '✓', 'red', null, null),
  exp_deployed: colDef('exp_deployed', 'expDeployed', '🚀', 'red', null, null),
}))

const standardItems = computed(() => {
  const c = standardCols.value
  return [
    { type: 'single', col: c.backlog },
    { type: 'single', col: c.ready },
    { type: 'group', title: c.analysis.label, active: c.analysis, done: c.analysis_done, wipLimit: wip.value.analysis, wipCount: counts.value.analysis },
    { type: 'group', title: c.development.label, active: c.development, done: c.dev_done, wipLimit: wip.value.development, wipCount: counts.value.development },
    { type: 'group', title: c.test.label, active: c.test, done: c.test_done, wipLimit: wip.value.test, wipCount: counts.value.test },
    { type: 'single', col: c.deployed },
  ]
})

const expediteItems = computed(() => {
  const c = expediteCols.value
  return [
    { type: 'single', col: c.exp_backlog },
    { type: 'single', col: c.exp_ready },
    { type: 'group', title: c.exp_analysis.label, active: c.exp_analysis, done: c.exp_analysis_done, wipLimit: wip.value.analysis, wipCount: counts.value.exp_analysis },
    { type: 'group', title: c.exp_development.label, active: c.exp_development, done: c.exp_dev_done, wipLimit: wip.value.development, wipCount: counts.value.exp_development },
    { type: 'group', title: c.exp_test.label, active: c.exp_test, done: c.exp_test_done, wipLimit: wip.value.test, wipCount: counts.value.exp_test },
    { type: 'single', col: c.exp_deployed },
  ]
})
</script>
