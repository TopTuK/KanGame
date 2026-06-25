<template>
  <div
    :draggable="canDrag"
    @dragstart="onCardDragStart"
    @dragend="onCardDragEnd"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onMemberDrop"
    :class="[
      'rounded-lg border transition-all duration-200 select-none text-white',
      cardBaseClass,
      canDrag ? 'cursor-grab active:cursor-grabbing hover:scale-[1.02] hover:shadow-lg' : 'cursor-default opacity-80',
      card.is_blocked ? 'opacity-50 border-dashed' : '',
      isDragging ? 'opacity-30 scale-95' : '',
      isActiveDropTarget && isDragOver ? 'ring-2 ring-emerald-400/80 shadow-lg shadow-emerald-950/40' : '',
    ]"
  >
    <!-- Card header -->
    <div :class="['px-3 py-2 rounded-t-lg flex items-start justify-between gap-1', cardHeaderClass]">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-1.5 mb-0.5">
          <span class="font-mono text-xs opacity-80 flex-shrink-0">{{ card.card_key }}</span>
          <span v-if="isExpedite" class="text-xs px-1 rounded bg-red-500/50">{{ t('card.expedite') }}</span>
          <span v-if="isFixedDate" class="text-xs px-1 rounded bg-yellow-500/50">{{ t('card.deadline') }}</span>
        </div>
        <div class="text-xs font-medium leading-tight truncate">{{ cardTitle(card) }}</div>
      </div>
      <span class="text-base flex-shrink-0">{{ typeIcon }}</span>
    </div>

    <!-- Progress bars + assignments -->
    <div class="px-3 py-2 space-y-1.5 bg-black/20 rounded-b-lg">
      <!-- Analysis -->
      <div v-if="card.analysis_total > 0" class="flex items-center gap-2">
        <span class="text-xs w-4 text-center opacity-60">A</span>
        <div class="flex-1 h-1.5 bg-black/30 rounded-full overflow-hidden">
          <div
            class="h-full bg-violet-400 rounded-full transition-all duration-300"
            :style="{ width: analysisPct + '%' }"
          ></div>
        </div>
        <span class="text-xs font-mono opacity-70 w-8 text-right">{{ fmtPts(card.analysis_remaining) }}</span>
      </div>

      <!-- Dev -->
      <div v-if="card.dev_total > 0" class="flex items-center gap-2">
        <span class="text-xs w-4 text-center opacity-60">D</span>
        <div class="flex-1 h-1.5 bg-black/30 rounded-full overflow-hidden">
          <div
            class="h-full bg-sky-400 rounded-full transition-all duration-300"
            :style="{ width: devPct + '%' }"
          ></div>
        </div>
        <span class="text-xs font-mono opacity-70 w-8 text-right">{{ fmtPts(card.dev_remaining) }}</span>
      </div>

      <!-- Test -->
      <div v-if="card.test_total > 0" class="flex items-center gap-2">
        <span class="text-xs w-4 text-center opacity-60">T</span>
        <div class="flex-1 h-1.5 bg-black/30 rounded-full overflow-hidden">
          <div
            class="h-full bg-amber-400 rounded-full transition-all duration-300"
            :style="{ width: testPct + '%' }"
          ></div>
        </div>
        <span class="text-xs font-mono opacity-70 w-8 text-right">{{ fmtPts(card.test_remaining) }}</span>
      </div>

      <!-- Assigned members badges -->
      <div v-if="assignedMembers.length > 0" class="flex flex-wrap gap-1 pt-0.5">
        <div
          v-for="{ member, contribution } in assignedMembers"
          :key="member.id"
          :class="['flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-medium border', memberBadgeClass(member)]"
        >
          <span>{{ member.icon }}</span>
          <span class="font-mono">{{ member.id }}</span>
          <span class="opacity-70">+{{ fmtPts(contribution) }}</span>
        </div>
      </div>

      <!-- Member drop zone (only for active columns during capacity phase) -->
      <div
        v-if="isActiveDropTarget"
        :class="[
          'rounded border border-dashed text-center py-1.5 text-xs transition-all duration-150 mt-0.5',
          isDragOver
            ? 'border-emerald-400 bg-emerald-950/40 text-emerald-300'
            : store.currentDragMember
              ? 'border-slate-500/60 text-slate-500 bg-slate-800/20'
              : 'border-slate-700/40 text-slate-700',
        ]"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onMemberDrop"
      >
        <template v-if="isDragOver && previewContribution > 0">
          +{{ fmtPts(previewContribution) }} pts · {{ effLabel }}
        </template>
        <template v-else-if="isDragOver">
          {{ t('card.dropHere') }}
        </template>
        <template v-else>
          {{ t('card.assignMember') }}
        </template>
      </div>

      <!-- Ready to move indicator -->
      <div v-if="isReadyToMove && columnKey !== 'deployed'" class="flex items-center gap-1 pt-0.5">
        <div class="w-full text-center text-xs text-emerald-400 font-medium animate-pulse">
          {{ t('card.readyToPull') }}
        </div>
      </div>

      <!-- Fixed date info -->
      <div v-if="card.due_day" class="text-xs flex items-center gap-1 pt-0.5">
        <span class="opacity-60">{{ t('card.due') }}</span>
        <span :class="dueDateClass">{{ t('card.day', { day: card.due_day }) }}</span>
        <span v-if="card.penalty" class="opacity-60">(-${{ card.penalty }})</span>
      </div>

      <!-- Revenue info -->
      <div v-if="card.revenue_per_day && columnKey === 'deployed'" class="text-xs text-emerald-400 flex items-center gap-1 pt-0.5">
        <span>{{ t('card.revenuePerDay', { amount: card.revenue_per_day }) }}</span>
        <span v-if="card.deployed_day" class="opacity-60">{{ t('card.fromDay', { day: card.deployed_day }) }}</span>
      </div>

      <!-- Blocked -->
      <div v-if="card.is_blocked" class="text-xs text-red-400 flex items-center gap-1">
        🔒 {{ card.blocked_reason || t('card.blocked') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import { useGameContent } from '../composables/useGameContent.js'

const { t } = useI18n()
const { cardTitle } = useGameContent()

const props = defineProps({
  card: Object,
  columnKey: String,
})

const store = useGameStore()
const isDragging = ref(false)
const isDragOver = ref(false)

const ACTIVE_COLUMNS = ['analysis', 'development', 'test']

const isExpedite = computed(() => props.card.card_type === 'expedite')
const isFixedDate = computed(() => props.card.card_type === 'fixed_date')

const typeIcon = computed(() => ({
  standard: '📦', bug: '🐛', expedite: '🚨', fixed_date: '📅', intangible: '⚙️',
})[props.card.card_type] || '📦')

function fmtPts(n) {
  const v = Number(n) || 0
  return v === Math.floor(v) ? v.toFixed(0) : v.toFixed(1)
}

const analysisPct = computed(() => {
  if (!props.card.analysis_total) return 100
  return ((props.card.analysis_total - props.card.analysis_remaining) / props.card.analysis_total) * 100
})

const devPct = computed(() => {
  if (!props.card.dev_total) return 100
  return ((props.card.dev_total - props.card.dev_remaining) / props.card.dev_total) * 100
})

const testPct = computed(() => {
  if (!props.card.test_total) return 100
  return ((props.card.test_total - props.card.test_remaining) / props.card.test_total) * 100
})

const isReadyToMove = computed(() => {
  const col = props.columnKey
  const c = props.card
  if (col === 'options' || col === 'ready') return true
  if (col === 'analysis') return (c.analysis_remaining || 0) <= 0.01
  if (col === 'development') return (c.dev_remaining || 0) <= 0.01
  if (col === 'test') return (c.test_remaining || 0) <= 0.01
  return false
})

const canDrag = computed(() => {
  const phase = store.game?.phase
  if (!['capacity', 'move'].includes(phase)) return false
  if (props.card.is_blocked) return false
  return isReadyToMove.value
})

// Members currently assigned to THIS card
const assignedMembers = computed(() => {
  const result = []
  for (const [memberId, assignment] of Object.entries(store.memberAssignments)) {
    if (assignment.cardId === props.card.id) {
      const member = store.members.find(m => m.id === memberId)
      if (member) result.push({ member, contribution: assignment.contribution })
    }
  }
  return result
})

// Show drop zone only for active columns during capacity phase
const isActiveDropTarget = computed(() =>
  store.game?.phase === 'capacity' &&
  ACTIVE_COLUMNS.includes(props.columnKey) &&
  !props.card.is_blocked
)

// Preview contribution when hovering with a member
const previewContribution = computed(() => {
  if (!store.currentDragMember) return 0
  return store.getContribution(store.currentDragMember.id, props.columnKey)
})

const effLabel = computed(() => '')

const cardBaseClass = computed(() => ({
  blue:   'border-blue-600/60 bg-blue-900/40',
  red:    'border-red-600/60 bg-red-900/40',
  yellow: 'border-yellow-600/60 bg-yellow-900/40',
  gray:   'border-slate-600/60 bg-slate-800/60',
  orange: 'border-orange-600/60 bg-orange-900/40',
})[props.card.color] || 'border-slate-600/60 bg-slate-800/60')

const cardHeaderClass = computed(() => ({
  blue:   'bg-blue-800/50',
  red:    'bg-red-800/50',
  yellow: 'bg-yellow-800/50',
  gray:   'bg-slate-700/50',
  orange: 'bg-orange-800/50',
})[props.card.color] || 'bg-slate-700/50')

const dueDateClass = computed(() => {
  if (!store.game) return 'text-slate-400'
  const today = store.game.current_day
  const due = props.card.due_day
  if (today > due) return 'text-red-400 font-bold'
  if (today >= due - 2) return 'text-amber-400 font-semibold'
  return 'text-slate-300'
})

function memberBadgeClass(member) {
  const map = {
    analyst:   'bg-violet-900/60 border-violet-600/40 text-violet-200',
    developer: 'bg-sky-900/60 border-sky-600/40 text-sky-200',
    tester:    'bg-amber-900/60 border-amber-600/40 text-amber-200',
  }
  return map[member.role] || 'bg-slate-800/60 border-slate-600/40 text-slate-200'
}

// Card drag (move card between columns)
function onCardDragStart(e) {
  e.dataTransfer.setData('cardId', props.card.id)
  e.dataTransfer.effectAllowed = 'move'
  isDragging.value = true
}

function onCardDragEnd() {
  isDragging.value = false
}

// Member drop (assign team member to this card)
function onDragOver(e) {
  if (!isActiveDropTarget.value || !store.currentDragMember) return
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = true
  e.dataTransfer.dropEffect = 'copy'
}

function onDragLeave(e) {
  if (e.currentTarget.contains(e.relatedTarget)) return
  isDragOver.value = false
}

function onMemberDrop(e) {
  const memberId = e.dataTransfer.getData('memberId')
  if (!memberId) return
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false
  if (!isActiveDropTarget.value) return
  store.assignMember(memberId, props.card.id, props.columnKey)
}
</script>
