<template>
  <div class="flex flex-col w-52 flex-shrink-0 h-full">
    <!-- Column header -->
    <div :class="['rounded-t-xl px-3 py-2.5 flex items-center justify-between', headerClass]">
      <div class="flex items-center gap-2">
        <span class="text-base">{{ column.icon }}</span>
        <div>
          <div class="text-white font-semibold text-sm leading-tight">{{ column.label }}</div>
          <div class="text-xs opacity-70">{{ column.description }}</div>
        </div>
      </div>
      <div class="flex items-center gap-1.5">
        <!-- WIP indicator -->
        <div v-if="column.wipLimit" :class="['text-xs font-mono font-bold px-1.5 py-0.5 rounded', wipClass]">
          {{ cards.length }}/{{ column.wipLimit }}
        </div>
        <div v-else class="text-xs font-mono text-white/60">{{ cards.length }}</div>
      </div>
    </div>

    <!-- WIP limit warning bar -->
    <div v-if="column.wipLimit" class="h-1">
      <div
        :class="['h-full transition-all duration-300', wipBarClass]"
        :style="{ width: wipPercent + '%' }"
      ></div>
    </div>

    <!-- Cards area -->
    <div
      :class="[
        'flex-1 overflow-y-auto rounded-b-xl p-2 space-y-2',
        isAtLimit ? 'bg-red-950/20 border border-red-800/30' : 'bg-slate-800/50 border border-slate-700/30'
      ]"
      @dragover.prevent
      @drop="onDrop"
    >
      <KanbanCard
        v-for="card in cards"
        :key="card.id"
        :card="card"
        :column-key="column.key"
      />

      <!-- Empty state -->
      <div v-if="!cards.length" class="h-20 flex items-center justify-center">
        <p class="text-slate-600 text-xs text-center">{{ t('columns.dropCards') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import KanbanCard from './KanbanCard.vue'

const { t } = useI18n()

const props = defineProps({
  column: Object,
  cards: Array,
})

const store = useGameStore()

const wipPercent = computed(() => {
  if (!props.column.wipLimit) return 0
  return Math.min(100, (props.cards.length / props.column.wipLimit) * 100)
})

const isAtLimit = computed(() =>
  props.column.wipLimit && props.cards.length >= props.column.wipLimit
)

const colorMap = {
  slate:   { header: 'bg-slate-700',   bar: 'bg-slate-500' },
  violet:  { header: 'bg-violet-900',  bar: 'bg-violet-500' },
  sky:     { header: 'bg-sky-900',     bar: 'bg-sky-500' },
  amber:   { header: 'bg-amber-900',   bar: 'bg-amber-500' },
  emerald: { header: 'bg-emerald-900', bar: 'bg-emerald-500' },
  red:     { header: 'bg-red-900',     bar: 'bg-red-500' },
}

const headerClass = computed(() => colorMap[props.column.color]?.header || 'bg-slate-700')

const wipBarClass = computed(() => {
  if (!props.column.wipLimit) return ''
  const pct = wipPercent.value
  if (pct >= 100) return 'bg-red-500'
  if (pct >= 80) return 'bg-amber-500'
  return colorMap[props.column.color]?.bar || 'bg-sky-500'
})

const wipClass = computed(() => {
  if (!props.column.wipLimit) return ''
  const count = props.cards.length
  const limit = props.column.wipLimit
  if (count >= limit) return 'bg-red-500 text-white'
  if (count >= limit - 1) return 'bg-amber-500 text-black'
  return 'bg-white/20 text-white'
})

async function onDrop(e) {
  // Ignore member drops — those are handled by the card's own drop zone
  const memberId = e.dataTransfer.getData('memberId')
  if (memberId) return
  const cardId = e.dataTransfer.getData('cardId')
  if (!cardId) return
  await store.moveCard(cardId, props.column.key)
}
</script>
