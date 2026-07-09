<template>
  <div class="flex flex-col flex-shrink-0 rounded-xl border border-board-colborder/60 bg-board-col/40 overflow-hidden">
    <div :class="['px-2 py-2 flex items-center justify-between', headerClass]">
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="text-sm">{{ activeColumn.icon }}</span>
        <div class="min-w-0">
          <div class="text-white font-semibold text-xs leading-tight truncate">{{ title }}</div>
        </div>
      </div>
      <div v-if="displayWip" :class="['text-xs font-mono font-bold px-1 py-0.5 rounded flex-shrink-0', wipClass]">
        {{ displayWip }}
      </div>
    </div>

    <div class="flex items-start gap-1 p-1">
      <KanbanColumn
        :column="activeColumn"
        :cards="activeCards"
        :wip-count="activeColumn.wipCount"
        bare
      />
      <KanbanColumn
        :column="doneColumn"
        :cards="doneCards"
        :wip-count="doneColumn.wipCount"
        bare
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import KanbanColumn from './KanbanColumn.vue'

const props = defineProps({
  title: String,
  activeColumn: Object,
  doneColumn: Object,
  activeCards: Array,
  doneCards: Array,
  wipLimit: Number,
  wipCount: Number,
})

const colorMap = {
  slate: 'bg-slate-700',
  violet: 'bg-violet-900',
  sky: 'bg-sky-900',
  amber: 'bg-amber-900',
  emerald: 'bg-emerald-900',
  red: 'bg-red-900',
}

const headerClass = computed(() => colorMap[props.activeColumn.color] || 'bg-slate-700')

const displayWip = computed(() => {
  if (props.wipLimit != null && props.wipCount != null) {
    return `${props.wipCount}/${props.wipLimit}`
  }
  return null
})

const wipClass = computed(() => {
  if (!props.wipLimit) return ''
  const count = props.wipCount ?? (props.activeCards.length + props.doneCards.length)
  if (count >= props.wipLimit) return 'bg-red-500 text-white'
  if (count >= props.wipLimit - 1) return 'bg-amber-500 text-black'
  return 'bg-white/20 text-white'
})
</script>
