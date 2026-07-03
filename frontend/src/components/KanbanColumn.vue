<template>
  <div :class="['flex flex-col flex-shrink-0', column.pullable ? 'w-36' : 'w-44']">
    <div :class="['rounded-t-xl px-2 py-2 flex items-center justify-between', headerClass]">
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="text-sm">{{ column.icon }}</span>
        <div class="min-w-0">
          <div class="text-white font-semibold text-xs leading-tight truncate">{{ column.label }}</div>
        </div>
      </div>
      <div v-if="displayWip" :class="['text-xs font-mono font-bold px-1 py-0.5 rounded flex-shrink-0', wipClass]">
        {{ displayWip }}
      </div>
      <div v-else-if="!column.wipLimit" class="text-xs font-mono text-white/60">{{ cards.length }}</div>
    </div>

    <div
      :data-column="column.key"
      @dragover="onListDragOver"
      @dragenter="onListDragEnter"
      @dragleave="onListDragLeave"
      @drop="onListDrop"
      :class="[
        'flex-1 overflow-y-auto rounded-b-xl p-1.5 space-y-1.5 min-h-[80px] transition-all',
        isAtLimit ? 'bg-red-950/20 border border-red-800/30' : 'bg-slate-800/50 border border-slate-700/30',
        isCardDropTargetColumn ? (cardDropValid ? 'ring-2 ring-emerald-400' : 'ring-2 ring-red-500/70') : '',
      ]"
    >
      <div
        v-if="isCardDragOver && isCardDropTargetColumn"
        class="text-[9px] text-center py-1 rounded border"
        :class="cardDropValid ? 'text-emerald-300 bg-emerald-950/40 border-emerald-700/30' : 'text-red-300 bg-red-950/40 border-red-700/30'"
      >
        {{ t('columns.dropCards') }}
      </div>

      <KanbanCard
        v-for="card in cards"
        :key="card.id"
        :card="card"
        :column-key="column.key"
      />

      <div v-if="!cards.length" class="h-12 flex items-center justify-center">
        <p class="text-slate-600 text-[10px] text-center">—</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import KanbanCard from './KanbanCard.vue'

const { t } = useI18n()
const store = useGameStore()

const props = defineProps({
  column: Object,
  cards: Array,
  wipCount: Number,
})

const isCardDragOver = ref(false)
const isCardDropTargetColumn = computed(() => store.draggingCard?.toColumn === props.column.key)
const cardDropValid = computed(() => isCardDropTargetColumn.value && store.canDropOnColumn(props.column.key))

function onListDragOver(event) {
  if (!store.draggingCard || !isCardDropTargetColumn.value) return
  event.preventDefault()
  event.dataTransfer.dropEffect = cardDropValid.value ? 'move' : 'none'
}

function onListDragEnter(event) {
  if (!store.draggingCard || !isCardDropTargetColumn.value) return
  event.preventDefault()
  isCardDragOver.value = true
}

function onListDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isCardDragOver.value = false
  }
}

function onListDrop(event) {
  isCardDragOver.value = false
  if (!store.draggingCard || !cardDropValid.value) return
  const raw = event.dataTransfer.getData('cardId') || event.dataTransfer.getData('text/plain')
  const cardId = raw?.startsWith('card:') ? raw.slice('card:'.length) : raw
  if (cardId) {
    event.preventDefault()
    store.pullCard(cardId)
  }
}

const displayWip = computed(() => {
  if (props.column.wipLimit != null && props.wipCount != null) {
    return `${props.wipCount}/${props.column.wipLimit}`
  }
  return null
})

const isAtLimit = computed(() =>
  props.column.wipLimit != null && props.wipCount != null && props.wipCount >= props.column.wipLimit
)

const colorMap = {
  slate: 'bg-slate-700',
  violet: 'bg-violet-900',
  sky: 'bg-sky-900',
  amber: 'bg-amber-900',
  emerald: 'bg-emerald-900',
  red: 'bg-red-900',
}

const headerClass = computed(() => colorMap[props.column.color] || 'bg-slate-700')

const wipClass = computed(() => {
  if (!props.column.wipLimit) return ''
  const count = props.wipCount ?? props.cards.length
  const limit = props.column.wipLimit
  if (count >= limit) return 'bg-red-500 text-white'
  if (count >= limit - 1) return 'bg-amber-500 text-black'
  return 'bg-white/20 text-white'
})
</script>
