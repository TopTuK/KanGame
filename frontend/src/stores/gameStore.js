import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gamesApi } from '../services/api.js'

const STANDARD_COLUMNS = [
  'backlog', 'ready', 'analysis', 'analysis_done',
  'development', 'dev_done', 'test', 'deployed',
]
const EXPEDITE_COLUMNS = [
  'exp_backlog', 'exp_ready', 'exp_analysis', 'exp_analysis_done',
  'exp_development', 'exp_dev_done', 'exp_test', 'exp_deployed',
]
const PULLABLE = new Set([
  'ready', 'analysis_done', 'dev_done',
  'exp_ready', 'exp_analysis_done', 'exp_dev_done',
])
const ACTIVE_WORK = new Set([
  'analysis', 'development', 'test',
  'exp_analysis', 'exp_development', 'exp_test',
])
const CARD_DRAG_SOURCES = new Set([...PULLABLE, 'backlog', 'exp_backlog'])
// Mirrors the backend's PULL_WIP_KEYS — which wipCounts/wip_limits entry
// gates a card leaving this column.
const CARD_WIP_KEYS = {
  backlog: 'ready',
  ready: 'analysis',
  analysis_done: 'development',
  dev_done: 'test',
  exp_backlog: 'expedite',
  exp_ready: 'exp_analysis',
  exp_analysis_done: 'exp_development',
  exp_dev_done: 'exp_test',
}

export const useGameStore = defineStore('game', () => {
  const game = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const selectedWorkerIds = ref([])
  const draggingWorkerId = ref(null)
  const draggingCard = ref(null) // { id, fromColumn, toColumn } | null
  const workLog = ref([])
  const endDayModal = ref(null)
  const showWorkLog = ref(false)

  const cardsByColumn = computed(() => {
    if (!game.value) return {}
    const map = {}
    const all = [...STANDARD_COLUMNS, ...EXPEDITE_COLUMNS, 'hidden', 'removed']
    for (const col of all) {
      const inColumn = game.value.cards.filter(c => c.column === col)
      map[col] = col === 'backlog' || col === 'exp_backlog'
        ? inColumn.sort((a, b) => b.val - a.val)
        : inColumn.sort((a, b) => a.sort_order - b.sort_order)
    }
    return map
  })

  const isGameOver = computed(() => game.value?.status === 'completed')

  const workers = computed(() => game.value?.team_config?.workers || [])

  const assignedWorkersByCard = computed(() => {
    const map = {}
    for (const w of workers.value) {
      if (w.assigned_card_id) {
        if (!map[w.assigned_card_id]) map[w.assigned_card_id] = []
        map[w.assigned_card_id].push(w)
      }
    }
    return map
  })

  const wipCounts = computed(() => {
    if (!game.value) return {}
    const cards = game.value.cards
    const count = (cols) => cards.filter(c => cols.includes(c.column)).length
    return {
      ready: count(['ready']),
      analysis: count(['analysis', 'analysis_done']),
      development: count(['development', 'dev_done']),
      test: count(['test']),
      exp_analysis: count(['exp_analysis', 'exp_analysis_done']),
      exp_development: count(['exp_development', 'exp_dev_done']),
      exp_test: count(['exp_test']),
      expedite: count(['exp_ready']),
    }
  })

  function isPullableColumn(col) {
    return PULLABLE.has(col)
  }

  function nextColumnFor(col) {
    for (const arr of [STANDARD_COLUMNS, EXPEDITE_COLUMNS]) {
      const idx = arr.indexOf(col)
      if (idx >= 0 && idx + 1 < arr.length) return arr[idx + 1]
    }
    return null
  }

  function isDraggableCardColumn(col) {
    return CARD_DRAG_SOURCES.has(col)
  }

  function canDropOnColumn(targetColumn) {
    if (!draggingCard.value || draggingCard.value.toColumn !== targetColumn) return false
    const wipKey = CARD_WIP_KEYS[draggingCard.value.fromColumn]
    if (!wipKey) return true
    const limit = game.value?.wip_limits?.[wipKey]
    if (limit == null) return true
    return (wipCounts.value[wipKey] ?? 0) < limit
  }

  function startDragCard(cardId, fromColumn) {
    if (!canPlan() || loading.value) return
    if (!isDraggableCardColumn(fromColumn)) return
    draggingCard.value = { id: cardId, fromColumn, toColumn: nextColumnFor(fromColumn) }
  }

  function stopDragCard() {
    draggingCard.value = null
  }

  function isActiveWorkColumn(col) {
    return ACTIVE_WORK.has(col)
  }

  function canPlan() {
    return game.value?.phase === 'planning' && !game.value?.work_done
  }

  function canPullCard(fromColumn) {
    if (!canPlan() || loading.value) return false
    const wipKey = CARD_WIP_KEYS[fromColumn]
    if (!wipKey) return true
    const limit = game.value?.wip_limits?.[wipKey]
    if (limit == null) return true
    return (wipCounts.value[wipKey] ?? 0) < limit
  }

  async function loadGame(id) {
    loading.value = true
    error.value = null
    try {
      const res = await gamesApi.get(id)
      game.value = res.data
      clearSelectedWorkers()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function selectWorker(workerId) {
    if (!canPlan() || loading.value) return
    const w = workers.value.find(x => x.id === workerId)
    if (!w?.active || w.assigned_card_id) return
    selectedWorkerIds.value = selectedWorkerIds.value.includes(workerId)
      ? selectedWorkerIds.value.filter(id => id !== workerId)
      : [...selectedWorkerIds.value, workerId]
  }

  function clearSelectedWorkers() {
    selectedWorkerIds.value = []
  }

  function startDragWorker(workerId) {
    if (!canPlan() || loading.value) return
    const w = workers.value.find(x => x.id === workerId)
    if (!w?.active) return
    draggingWorkerId.value = workerId
    clearSelectedWorkers()
  }

  function stopDragWorker() {
    draggingWorkerId.value = null
  }

  async function assignWorker(workerId, cardId, options = {}) {
    const { clearSelection = true } = options
    if (!workerId || !game.value || !canPlan() || loading.value) return
    loading.value = true
    error.value = null
    if (clearSelection) clearSelectedWorkers()
    try {
      const res = await gamesApi.assignWorker(game.value.id, workerId, cardId)
      game.value = res.data
      draggingWorkerId.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function unassignWorker(workerId) {
    const w = workers.value.find(x => x.id === workerId)
    if (!w?.assigned_card_id) return
    return assignWorker(workerId, w.assigned_card_id)
  }

  async function assignToCard(cardId) {
    if (!selectedWorkerIds.value.length || !game.value || !canPlan() || loading.value) return
    const workerIds = [...selectedWorkerIds.value]
    clearSelectedWorkers()
    loading.value = true
    error.value = null
    try {
      for (const workerId of workerIds) {
        const worker = workers.value.find(w => w.id === workerId)
        if (worker?.assigned_card_id === cardId) continue
        const res = await gamesApi.assignWorker(game.value.id, workerId, cardId)
        game.value = res.data
      }
      clearSelectedWorkers()
      draggingWorkerId.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function pullCard(cardId) {
    if (!game.value) return
    loading.value = true
    error.value = null
    try {
      const res = await gamesApi.pullCard(game.value.id, cardId)
      game.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function startWork() {
    if (!game.value) return
    loading.value = true
    error.value = null
    try {
      const res = await gamesApi.startWork(game.value.id)
      game.value = res.data.game
      workLog.value = res.data.log || []
      showWorkLog.value = true
      clearSelectedWorkers()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function endDay() {
    if (!game.value) return
    loading.value = true
    error.value = null
    try {
      const res = await gamesApi.endDay(game.value.id)
      game.value = res.data.game
      endDayModal.value = res.data.modal
      showWorkLog.value = false
      workLog.value = []
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  function dismissEndDayModal() {
    endDayModal.value = null
  }

  function dismissWorkLog() {
    showWorkLog.value = false
  }

  return {
    game, loading, error,
    selectedWorkerIds, draggingWorkerId, draggingCard, workLog, showWorkLog, endDayModal,
    cardsByColumn, isGameOver, workers, assignedWorkersByCard, wipCounts,
    isPullableColumn, isActiveWorkColumn, isDraggableCardColumn, canDropOnColumn, canPlan, canPullCard,
    loadGame, selectWorker, clearSelectedWorkers, startDragWorker, stopDragWorker,
    startDragCard, stopDragCard,
    assignWorker, unassignWorker, assignToCard,
    pullCard,
    startWork, endDay, dismissEndDayModal, dismissWorkLog,
    STANDARD_COLUMNS, EXPEDITE_COLUMNS,
  }
})
