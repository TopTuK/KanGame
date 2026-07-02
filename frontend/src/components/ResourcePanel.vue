<template>
  <div class="px-4 py-2 flex items-center gap-4 min-h-[68px] border-b border-slate-700/50 bg-slate-900/80 flex-shrink-0">
    <div class="flex-shrink-0 w-48 text-xs leading-relaxed text-slate-400">
      <template v-if="store.canPlan()">
        <span class="text-violet-400 font-semibold block mb-0.5">{{ t('resources.planning') }}</span>
        {{ t('resources.planningHint') }}
        <span class="block text-slate-500">{{ t('resources.moveHint') }}</span>
      </template>
      <template v-else-if="store.game?.work_done">
        <span class="text-emerald-400 font-semibold block mb-0.5">{{ t('resources.workDone') }}</span>
        {{ t('resources.endDayHint') }}
      </template>
      <template v-else-if="store.game?.phase === 'completed'">
        <span class="text-amber-400 font-semibold">{{ t('resources.gameOver') }}</span>
      </template>
    </div>

    <div class="h-10 w-px bg-slate-700/60 flex-shrink-0"></div>

    <div class="flex items-center gap-4 flex-1 flex-wrap">
      <div v-for="group in roleGroups" :key="group.role" class="flex items-center gap-1">
        <div :class="['w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold', group.labelCls]">
          {{ group.letter }}
        </div>
        <div
          v-for="w in group.workers"
          :key="w.id"
          role="button"
          tabindex="0"
          :draggable="canDragWorker(w)"
          @dragstart="onWorkerDragStart($event, w)"
          @dragend="onWorkerDragEnd"
          @click="onWorkerClick(w)"
          @keydown.enter.prevent="onWorkerClick(w)"
          @keydown.space.prevent="onWorkerClick(w)"
          :title="workerTitle(w)"
          :class="[
            'w-9 h-9 rounded-full flex items-center justify-center text-sm border-2 transition-all',
            workerCls(w),
            store.selectedWorkerIds.includes(w.id) ? 'ring-2 ring-white scale-110' : '',
            store.draggingWorkerId === w.id ? 'opacity-40 scale-90' : '',
            workerInteractionCls(w),
          ]"
        >
          {{ roleIcon(w.type) }}
        </div>
      </div>
    </div>

    <div class="h-10 w-px bg-slate-700/60 flex-shrink-0"></div>

    <div class="flex items-center gap-2 flex-shrink-0">
      <button
        v-if="store.canPlan()"
        @click="store.startWork()"
        :disabled="store.loading"
        class="btn-primary text-sm py-2 px-5"
      >
        {{ t('resources.startWork') }}
      </button>
      <span v-if="store.game?.carlos_policy" class="text-[10px] text-amber-400 px-2 py-1 rounded bg-amber-950/50 border border-amber-800/40">
        Carlos
      </span>
      <span v-if="store.game?.lockdown" class="text-[10px] text-red-400 px-2 py-1 rounded bg-red-950/50 border border-red-800/40">
        Lockdown
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'

const { t } = useI18n()
const store = useGameStore()
const suppressNextClick = ref(false)

const roleGroups = computed(() => {
  const workers = store.workers
  return [
    {
      role: 'analyst', letter: 'A', labelCls: 'bg-violet-900/80 text-violet-300',
      workers: workers.filter(w => w.type === 'analyst'),
    },
    {
      role: 'developer', letter: 'D', labelCls: 'bg-sky-900/80 text-sky-300',
      workers: workers.filter(w => w.type === 'developer'),
    },
    {
      role: 'tester', letter: 'T', labelCls: 'bg-amber-900/80 text-amber-300',
      workers: workers.filter(w => w.type === 'tester'),
    },
  ]
})

function roleIcon(type) {
  return { analyst: '🔍', developer: '💻', tester: '🧪' }[type] || '👤'
}

function workerCls(w) {
  if (!w.active) return 'border-slate-700 bg-slate-800/50'
  const map = {
    analyst: 'border-violet-500 bg-violet-950/60',
    developer: 'border-sky-500 bg-sky-950/60',
    tester: 'border-amber-500 bg-amber-950/60',
  }
  return map[w.type] || 'border-slate-500 bg-slate-800'
}

function workerInteractionCls(w) {
  if (!w.active || !store.canPlan() || store.loading) return 'opacity-30 cursor-not-allowed'
  if (w.assigned_card_id) return 'opacity-50 cursor-pointer hover:opacity-80'
  return 'hover:scale-105 cursor-grab active:cursor-grabbing'
}

function workerTitle(w) {
  if (!w.active) return t('resources.unavailable')
  const specCol = { analyst: 'Analysis (2d6)', developer: 'Development (2d6)', tester: 'Test (2d6)' }[w.type] || ''
  const hint = specCol ? `Specialist: ${specCol} · Non-specialist: 1d6` : ''
  if (w.assigned_card_id) return `${w.id} → assigned | click to unassign | ${hint}`
  return `${w.id} | ${hint} · Drag or click to assign`
}

function canDragWorker(w) {
  return w.active && !w.assigned_card_id && store.canPlan() && !store.loading
}

function onWorkerClick(w) {
  if (suppressNextClick.value) {
    suppressNextClick.value = false
    return
  }
  if (!w.active || !store.canPlan() || store.loading) return
  if (w.assigned_card_id) {
    store.unassignWorker(w.id)
    return
  }
  store.selectWorker(w.id)
}

function onWorkerDragStart(event, w) {
  if (!canDragWorker(w)) {
    event.preventDefault()
    return
  }
  event.dataTransfer.setData('workerId', w.id)
  event.dataTransfer.setData('text/plain', `worker:${w.id}`)
  event.dataTransfer.effectAllowed = 'copy'
  store.startDragWorker(w.id)
}

function onWorkerDragEnd() {
  suppressNextClick.value = true
  store.stopDragWorker()
  window.setTimeout(() => {
    suppressNextClick.value = false
  }, 0)
}
</script>
