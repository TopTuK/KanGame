<template>
  <div class="flex gap-3 h-full min-w-max pb-2">
    <KanbanColumn
      v-for="col in columns"
      :key="col.key"
      :column="col"
      :cards="store.cardsByColumn[col.key] || []"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import KanbanColumn from './KanbanColumn.vue'

const { t } = useI18n()
const store = useGameStore()

const columns = computed(() => {
  const wip = store.game?.wip_limits || {}
  return [
    { key: 'options',     label: t('columns.options.label'),     icon: '📋', wipLimit: null,            color: 'slate',  description: t('columns.options.description') },
    { key: 'ready',       label: t('columns.ready.label'),       icon: '✅', wipLimit: null,            color: 'slate',  description: t('columns.ready.description') },
    { key: 'analysis',    label: t('columns.analysis.label'),    icon: '🔍', wipLimit: wip.analysis,    color: 'violet', description: t('columns.analysis.description', { limit: wip.analysis }) },
    { key: 'development', label: t('columns.development.label'), icon: '💻', wipLimit: wip.development, color: 'sky',    description: t('columns.development.description', { limit: wip.development }) },
    { key: 'test',        label: t('columns.test.label'),        icon: '🧪', wipLimit: wip.test,        color: 'amber',  description: t('columns.test.description', { limit: wip.test }) },
    { key: 'deployed',    label: t('columns.deployed.label'),    icon: '🚀', wipLimit: null,            color: 'emerald', description: t('columns.deployed.description') },
  ]
})
</script>
