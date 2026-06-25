<template>
  <div class="p-4 flex-shrink-0">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Team Capacity</h3>
      <span class="text-xs text-slate-500">Day {{ store.game?.current_day }}</span>
    </div>

    <!-- Capacity bars -->
    <div class="space-y-3">
      <div v-for="role in roles" :key="role.key" :class="['rounded-lg p-2.5', role.bgClass]">
        <div class="flex items-center justify-between mb-1.5">
          <div class="flex items-center gap-1.5">
            <span class="text-sm">{{ role.icon }}</span>
            <span class="text-xs font-medium text-slate-300">{{ role.label }}</span>
          </div>
          <span class="text-xs font-mono text-white">
            <span class="text-emerald-400">{{ store.capacityRemaining[role.key] }}</span>/{{ store.teamCapacity[role.key] }}
          </span>
        </div>
        <div class="h-1.5 bg-black/30 rounded-full overflow-hidden">
          <div
            :class="['h-full rounded-full transition-all duration-500', role.barClass]"
            :style="{ width: capacityUsedPct(role.key) + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Quick allocate -->
    <div v-if="store.game?.phase === 'capacity'" class="mt-4">
      <button
        @click="showAllocate = !showAllocate"
        class="w-full btn-secondary text-sm py-2"
      >
        {{ showAllocate ? '▲ Hide' : '▼ Allocate Capacity' }}
      </button>

      <div v-if="showAllocate" class="mt-3 space-y-2 max-h-64 overflow-y-auto pr-1">
        <div
          v-for="card in activeCards"
          :key="card.id"
          class="glass rounded-lg p-2.5"
        >
          <div class="flex items-center justify-between mb-1.5">
            <div class="min-w-0">
              <span class="text-xs text-slate-400 font-mono mr-1">{{ card.card_key }}</span>
              <span class="text-xs text-white">{{ card.title.slice(0, 22) }}{{ card.title.length > 22 ? '…' : '' }}</span>
            </div>
            <span class="text-sm ml-1 flex-shrink-0">{{ columnEmoji(card.column) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <input
              v-model.number="allocation[card.id]"
              type="number"
              min="0"
              :max="maxForCard(card)"
              placeholder="0"
              class="w-14 px-2 py-1 bg-slate-700 border border-slate-600 rounded text-white text-sm text-center focus:outline-none focus:border-sky-500"
            />
            <span class="text-xs text-slate-400">of {{ remainingForCard(card) }} pts</span>
          </div>
        </div>

        <button
          v-if="activeCards.length"
          @click="submitAllocations"
          :disabled="store.loading"
          class="w-full btn-primary text-sm py-2 mt-1"
        >
          Apply
        </button>
        <p v-else class="text-xs text-slate-500 text-center py-3">
          Pull cards into active columns first.
        </p>
      </div>
    </div>

    <!-- Phase hint -->
    <div class="mt-4 p-2.5 bg-slate-800/40 rounded-lg text-xs text-slate-400 leading-relaxed">
      <template v-if="store.game?.phase === 'event'">
        <span class="text-sky-400 font-medium">Next:</span> Click "Read Event" to start the day
      </template>
      <template v-else-if="store.game?.phase === 'capacity'">
        <span class="text-sky-400 font-medium">Now:</span> Allocate capacity to cards in active columns, then drag ready cards forward
      </template>
      <template v-else-if="store.game?.phase === 'move'">
        <span class="text-sky-400 font-medium">Now:</span> Drag completed cards to next column, then End Day
      </template>
      <template v-else-if="store.game?.phase === 'completed'">
        <span class="text-emerald-400 font-medium">Done!</span> Game over — see your final score above
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGameStore } from '../stores/gameStore.js'

const store = useGameStore()
const showAllocate = ref(false)
const allocation = ref({})

const roles = [
  { key: 'analysis',    label: 'Analysis',    icon: '🔍', bgClass: 'bg-violet-950/40', barClass: 'bg-violet-500' },
  { key: 'development', label: 'Development', icon: '💻', bgClass: 'bg-sky-950/40',    barClass: 'bg-sky-500' },
  { key: 'test',        label: 'Test',        icon: '🧪', bgClass: 'bg-amber-950/40',  barClass: 'bg-amber-500' },
]

function capacityUsedPct(role) {
  const total = store.teamCapacity[role] || 1
  const used = (store.game?.day_capacity_used?.[role] || 0)
  return Math.min(100, (used / total) * 100)
}

const activeCards = computed(() => {
  if (!store.game) return []
  return store.game.cards.filter(c =>
    ['analysis', 'development', 'test'].includes(c.column) && !c.is_blocked
  )
})

function remainingForCard(card) {
  if (card.column === 'analysis') return card.analysis_remaining
  if (card.column === 'development') return card.dev_remaining
  if (card.column === 'test') return card.test_remaining
  return 0
}

function maxForCard(card) {
  const remaining = remainingForCard(card)
  const cap = store.capacityRemaining[card.column] || 0
  return Math.min(remaining, cap)
}

function columnEmoji(col) {
  return { analysis: '🔍', development: '💻', test: '🧪' }[col] || ''
}

async function submitAllocations() {
  const allocs = Object.entries(allocation.value)
    .filter(([, pts]) => pts > 0)
    .map(([card_id, points]) => ({ card_id, points }))
  if (!allocs.length) return
  await store.allocateCapacity(allocs)
  allocation.value = {}
}
</script>
