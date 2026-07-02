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
      :class="[
        'flex-1 overflow-y-auto rounded-b-xl p-1.5 space-y-1.5 min-h-[80px]',
        isAtLimit ? 'bg-red-950/20 border border-red-800/30' : 'bg-slate-800/50 border border-slate-700/30',
      ]"
    >
      <div v-if="column.key === 'backlog'" class="space-y-1 pb-1">
        <button
          v-for="opt in backlogPullOptions"
          :key="opt.type"
          :disabled="!store.canPlan() || store.loading || opt.count === 0"
          @click="store.pullBacklog(opt.type)"
          class="w-full py-1 text-[9px] font-semibold rounded bg-emerald-900/50 text-emerald-300 border border-emerald-700/40 hover:bg-emerald-800/60 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-emerald-900/50"
        >
          {{ t(`pull.${opt.labelKey}`) }} ({{ opt.count }}) →
        </button>
      </div>

      <div v-else-if="column.key === 'exp_backlog'" class="pb-1">
        <button
          :disabled="!store.canPlan() || store.loading || cards.length === 0"
          @click="store.pullExpedite()"
          class="w-full py-1 text-[9px] font-semibold rounded bg-red-900/50 text-red-300 border border-red-700/40 hover:bg-red-800/60 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-red-900/50"
        >
          {{ t('pull.expedite') }} ({{ cards.length }}) →
        </button>
      </div>

      <KanbanCard
        v-for="card in cards"
        :key="card.id"
        :card="card"
        :column-key="column.key"
        :pullable="column.pullable"
      />

      <div v-if="!cards.length" class="h-12 flex items-center justify-center">
        <p class="text-slate-600 text-[10px] text-center">—</p>
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
const store = useGameStore()

const props = defineProps({
  column: Object,
  cards: Array,
  wipCount: Number,
})

const BACKLOG_TYPES = [
  { type: 's', labelKey: 'standard', cardType: 'standard' },
  { type: 'f', labelKey: 'fixed', cardType: 'fixed_date' },
  { type: 'i', labelKey: 'intangible', cardType: 'intangible' },
]

const backlogPullOptions = computed(() =>
  BACKLOG_TYPES.map(opt => ({
    ...opt,
    count: props.cards.filter(c => c.card_type === opt.cardType).length,
  }))
)

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
