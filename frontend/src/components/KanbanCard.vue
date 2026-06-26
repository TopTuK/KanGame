<template>
  <div
    @click="onCardClick"
    @dragover="onDragOver"
    @dragenter="onDragEnter"
    @dragleave="onDragLeave"
    @drop="onDrop"
    :class="[
      'rounded-lg border transition-all duration-200 select-none overflow-hidden cursor-pointer',
      cardBorderClass,
      card.is_blocked ? 'ring-1 ring-red-500/50' : '',
      ringClass,
    ]"
  >
    <div :class="['px-2 py-1.5 flex items-center justify-between gap-1', cardHeaderClass]">
      <div class="flex items-center gap-1 min-w-0">
        <span class="font-mono text-[10px] font-bold text-white/90">{{ card.card_key }}</span>
        <span v-if="isExpedite" class="text-[9px] px-1 rounded bg-red-500/60 text-red-100">⚡</span>
        <span v-else-if="isFixedDate" class="text-[9px] px-1 rounded bg-yellow-500/50 text-yellow-100">📅</span>
        <span v-else-if="isIntangible" class="text-[9px] px-1 rounded bg-slate-500/50">⚙️</span>
      </div>
      <span v-if="headerValue" :class="['text-[10px] font-mono font-bold', headerValueClass]">{{ headerValue }}</span>
    </div>

    <div :class="['px-2 pb-1 text-[10px] font-medium leading-tight text-white/75 line-clamp-2', cardBodyBgClass]">
      {{ cardTitle(card) }}
    </div>

    <div :class="['px-2 pb-2 space-y-1', cardBodyBgClass]">
      <div v-if="card.analysis_total > 0" class="flex items-center gap-1">
        <span class="text-[9px] w-3 text-violet-300/70">🔍</span>
        <div class="flex-1 h-1 bg-black/30 rounded-full overflow-hidden">
          <div class="h-full bg-violet-400 rounded-full transition-all" :style="{ width: analysisPct + '%' }"></div>
        </div>
      </div>
      <div v-if="card.dev_total > 0" class="flex items-center gap-1">
        <span class="text-[9px] w-3 text-sky-300/70">💻</span>
        <div class="flex-1 h-1 bg-black/30 rounded-full overflow-hidden">
          <div class="h-full bg-sky-400 rounded-full transition-all" :style="{ width: devPct + '%' }"></div>
        </div>
      </div>
      <div v-if="card.test_total > 0" class="flex items-center gap-1">
        <span class="text-[9px] w-3 text-amber-300/70">🧪</span>
        <div class="flex-1 h-1 bg-black/30 rounded-full overflow-hidden">
          <div class="h-full bg-amber-400 rounded-full transition-all" :style="{ width: testPct + '%' }"></div>
        </div>
      </div>

      <div v-if="card.is_blocked && card.blocker_remaining > 0" class="flex items-center gap-1">
        <span class="text-[9px] w-3 text-orange-300/70">🚫</span>
        <div class="flex-1 h-1 bg-black/30 rounded-full overflow-hidden">
          <div
            class="h-full bg-orange-400 rounded-full"
            :style="{ width: blockerPct + '%' }"
          ></div>
        </div>
        <span class="text-[9px] text-orange-300">{{ card.blocker_remaining }}</span>
      </div>

      <!-- Assigned worker badges — click to unassign -->
      <div v-if="assignedWorkers.length" class="flex flex-wrap gap-0.5 pt-0.5">
        <button
          v-for="w in assignedWorkers"
          :key="w.id"
          @click.stop="store.unassignWorker(w.id)"
          :title="`${w.id} — click to unassign`"
          :class="[
            'text-[9px] px-1 py-0.5 rounded font-mono flex items-center gap-0.5 border border-transparent',
            'hover:opacity-70 hover:border-white/20 transition-opacity cursor-pointer',
            workerBadgeCls(w.type),
          ]"
        >
          <span class="leading-none">{{ roleIcon(w.type) }}</span>
          <span>{{ w.id }}</span>
        </button>
      </div>

      <!-- Drop hint shown when dragging a worker over this card -->
      <div
        v-if="isDragOver"
        class="text-[9px] text-center text-emerald-300 py-0.5 rounded bg-emerald-950/40 border border-emerald-700/30"
      >
        Drop to assign
      </div>

      <button
        v-if="pullable && store.canPlan()"
        @click.stop="store.pullCard(card.id)"
        class="w-full mt-0.5 py-0.5 text-[9px] font-semibold rounded bg-emerald-900/50 text-emerald-300 border border-emerald-700/40 hover:bg-emerald-800/60"
      >
        {{ t('card.pull') }} →
      </button>

      <div v-if="card.due_day" class="text-[9px] text-white/50">
        {{ t('card.due') }} {{ t('card.day', { day: card.due_day }) }}
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
const store = useGameStore()

const props = defineProps({
  card: Object,
  columnKey: String,
  pullable: Boolean,
})

const isDragOver = ref(false)

const isExpedite = computed(() => props.card.card_type === 'expedite')
const isFixedDate = computed(() => props.card.card_type === 'fixed_date')
const isIntangible = computed(() => props.card.card_type === 'intangible')

const assignedWorkers = computed(() =>
  store.assignedWorkersByCard[props.card.id] || []
)
const hasWorkers = computed(() => assignedWorkers.value.length > 0)

const isDropTarget = computed(() =>
  store.isActiveWorkColumn(props.columnKey) && store.canPlan()
)

const isSelectedTarget = computed(() =>
  store.selectedWorkerIds.length > 0 && isDropTarget.value
)

// Unified ring class — drag takes priority over click-selection
const ringClass = computed(() => {
  if (isDragOver.value) return 'ring-2 ring-emerald-400 shadow-lg shadow-emerald-900/40 scale-[1.02]'
  if (isSelectedTarget.value) return 'ring-2 ring-sky-400'
  if (hasWorkers.value) return 'ring-1 ring-emerald-500/40'
  return ''
})

function fmtRub(n) {
  return Number(n).toLocaleString('ru-RU') + ' ₽'
}

const headerValue = computed(() => {
  if (props.card.card_type === 'standard' && props.card.val) return fmtRub(props.card.val)
  if (isFixedDate.value || isExpedite.value) {
    if (props.card.val > 0) return '+' + fmtRub(props.card.val)
    if (props.card.val < 0) return fmtRub(props.card.val)
  }
  return ''
})

const headerValueClass = computed(() => {
  if (props.card.val < 0) return 'text-red-300'
  if (isExpedite.value) return 'text-amber-300'
  return 'text-emerald-300'
})

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
const blockerPct = computed(() => {
  if (!props.card.blocker_total) return 0
  return ((props.card.blocker_total - props.card.blocker_remaining) / props.card.blocker_total) * 100
})

const cardBorderClass = computed(() => ({
  blue: 'border-blue-600/50', red: 'border-red-600/50',
  yellow: 'border-yellow-600/50', gray: 'border-slate-600/50',
  orange: 'border-orange-600/50',
})[props.card.color] || 'border-slate-600/50')

const cardHeaderClass = computed(() => ({
  blue: 'bg-blue-800/70', red: 'bg-red-800/70',
  yellow: 'bg-yellow-800/60', gray: 'bg-slate-700/70',
  orange: 'bg-orange-800/60',
})[props.card.color] || 'bg-slate-700/70')

const cardBodyBgClass = computed(() => ({
  blue: 'bg-blue-950/60', red: 'bg-red-950/60',
  yellow: 'bg-yellow-950/50', gray: 'bg-slate-900/60',
  orange: 'bg-orange-950/50',
})[props.card.color] || 'bg-slate-900/60')

function roleIcon(type) {
  return { analyst: '🔍', developer: '💻', tester: '🧪' }[type] || '👤'
}

function workerBadgeCls(type) {
  return {
    analyst: 'bg-violet-900/70 text-violet-200',
    developer: 'bg-sky-900/70 text-sky-200',
    tester: 'bg-amber-900/70 text-amber-200',
  }[type] || 'bg-slate-800 text-slate-300'
}

// ── Drag & drop ──────────────────────────────────────────────────────────────

function onDragOver(event) {
  if (!isDropTarget.value || !store.draggingWorkerId) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'copy'
}

function onDragEnter(event) {
  if (!isDropTarget.value || !store.draggingWorkerId) return
  event.preventDefault()
  isDragOver.value = true
}

function onDragLeave(event) {
  // Only clear when the cursor truly leaves the card element
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false
  }
}

function onDrop(event) {
  isDragOver.value = false
  if (!isDropTarget.value) return
  const workerId = draggedWorkerId(event)
  if (workerId) {
    event.preventDefault()
    store.assignWorker(workerId, props.card.id)
  }
}

function draggedWorkerId(event) {
  const directId = event.dataTransfer.getData('workerId')
  if (directId) return directId
  const plain = event.dataTransfer.getData('text/plain')
  return plain?.startsWith('worker:') ? plain.slice('worker:'.length) : ''
}

// ── Click assignment (existing flow) ────────────────────────────────────────

function onCardClick() {
  if (!store.canPlan() || store.loading) return
  if (store.selectedWorkerIds.length > 0 && isDropTarget.value) {
    store.assignToCard(props.card.id)
  }
}
</script>
