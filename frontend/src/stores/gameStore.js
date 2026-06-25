import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gamesApi } from '../services/api.js'

export const useGameStore = defineStore('game', () => {
  const game = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Member drag state — shared so cards can show drop previews
  const currentDragMember = ref(null)

  // Pending assignments: memberId → { cardId, cardColumn, contribution }
  const memberAssignments = ref({})

  // ── Computed ──────────────────────────────────────────────────────────

  const cardsByColumn = computed(() => {
    if (!game.value) return {}
    const map = {}
    const columns = ['options', 'ready', 'analysis', 'development', 'test', 'deployed']
    for (const col of columns) {
      map[col] = game.value.cards
        .filter(c => c.column === col)
        .sort((a, b) => a.sort_order - b.sort_order)
    }
    return map
  })

  const todayEvent = computed(() => {
    if (!game.value) return null
    return game.value.events.find(
      e => e.day === game.value.current_day && !e.is_resolved
    ) || null
  })

  const isGameOver = computed(() => game.value?.status === 'completed')

  const teamCapacity = computed(() => {
    if (!game.value) return { analysis: 0, development: 0, test: 0 }
    const cfg = game.value.team_config
    const memberCaps = cfg.member_capacities
    const bonus = cfg.capacity_bonus || { analysis: 0, development: 0, test: 0 }
    if (!memberCaps) {
      return {
        analysis: (cfg.analyst_capacity || 2) * (cfg.analysts || 2) + (bonus.analysis || 0),
        development: (cfg.dev_capacity || 2) * (cfg.developers || 4) + (bonus.development || 0),
        test: (cfg.test_capacity || 2) * (cfg.testers || 3) + (bonus.test || 0),
      }
    }
    // Sum primary-role capacities only: analysts→analysis, devs→development, testers→test
    let analysis = 0, development = 0, test = 0
    for (let i = 0; i < (cfg.analysts || 2); i++) analysis += memberCaps[`A${i + 1}`]?.analysis || 0
    for (let i = 0; i < (cfg.developers || 4); i++) development += memberCaps[`D${i + 1}`]?.development || 0
    for (let i = 0; i < (cfg.testers || 3); i++) test += memberCaps[`T${i + 1}`]?.test || 0
    return {
      analysis: Math.round((analysis + (bonus.analysis || 0)) * 100) / 100,
      development: Math.round((development + (bonus.development || 0)) * 100) / 100,
      test: Math.round((test + (bonus.test || 0)) * 100) / 100,
    }
  })

  const capacityRemaining = computed(() => {
    if (!game.value) return { analysis: 0, development: 0, test: 0 }
    const used = game.value.day_capacity_used
    const total = teamCapacity.value
    return {
      analysis: Math.max(0, total.analysis - (used.analysis || 0)),
      development: Math.max(0, total.development - (used.development || 0)),
      test: Math.max(0, total.test - (used.test || 0)),
    }
  })

  const wipCounts = computed(() => {
    if (!game.value) return {}
    const cards = game.value.cards
    return {
      analysis: cards.filter(c => c.column === 'analysis').length,
      development: cards.filter(c => c.column === 'development').length,
      test: cards.filter(c => c.column === 'test').length,
    }
  })

  // Individual team members derived from team_config
  const members = computed(() => {
    if (!game.value) return []
    const cfg = game.value.team_config
    const memberCaps = cfg.member_capacities || {}
    const list = []
    for (let i = 0; i < (cfg.analysts || 2); i++) {
      const id = `A${i + 1}`
      list.push({ id, role: 'analyst', name: `Analyst ${i + 1}`, icon: '🔬', color: 'violet', capacity: memberCaps[id]?.analysis ?? 2 })
    }
    for (let i = 0; i < (cfg.developers || 4); i++) {
      const id = `D${i + 1}`
      list.push({ id, role: 'developer', name: `Dev ${i + 1}`, icon: '💻', color: 'sky', capacity: memberCaps[id]?.development ?? 2 })
    }
    for (let i = 0; i < (cfg.testers || 3); i++) {
      const id = `T${i + 1}`
      list.push({ id, role: 'tester', name: `Tester ${i + 1}`, icon: '🧪', color: 'amber', capacity: memberCaps[id]?.test ?? 2 })
    }
    return list
  })

  // Aggregated pending points per card (before applying to backend)
  const pendingAllocations = computed(() => {
    const totals = {}
    for (const [, { cardId, cardColumn, contribution }] of Object.entries(memberAssignments.value)) {
      if (!totals[cardId]) totals[cardId] = { column: cardColumn, points: 0 }
      totals[cardId].points = Math.round((totals[cardId].points + contribution) * 100) / 100
    }
    return totals
  })

  const hasAssignments = computed(() => Object.keys(memberAssignments.value).length > 0)

  // ── Member assignment helpers ─────────────────────────────────────────

  function getContribution(memberId, cardColumn) {
    const memberCaps = game.value?.team_config?.member_capacities
    if (memberCaps?.[memberId]) return memberCaps[memberId][cardColumn] || 0
    // Fallback for before resolve_event (event phase)
    const member = members.value.find(m => m.id === memberId)
    if (!member) return 0
    const FALLBACK = { analyst: { analysis: 1.0, development: 0.4, test: 0.6 }, developer: { analysis: 0.5, development: 1.2, test: 0.6 }, tester: { analysis: 0.5, development: 0.6, test: 1.1 } }
    return FALLBACK[member.role]?.[cardColumn] ?? 0
  }

  function assignMember(memberId, cardId, cardColumn) {
    const member = members.value.find(m => m.id === memberId)
    if (!member) return
    const contribution = getContribution(memberId, cardColumn)
    memberAssignments.value = { ...memberAssignments.value, [memberId]: { cardId, cardColumn, contribution } }
  }

  function unassignMember(memberId) {
    const copy = { ...memberAssignments.value }
    delete copy[memberId]
    memberAssignments.value = copy
  }

  function clearAssignments() {
    memberAssignments.value = {}
  }

  // ── Actions ───────────────────────────────────────────────────────────

  async function loadGame(id) {
    loading.value = true
    error.value = null
    try {
      const res = await gamesApi.get(id)
      game.value = res.data
      clearAssignments()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function resolveEvent() {
    if (!game.value) return
    loading.value = true
    try {
      const res = await gamesApi.resolveEvent(game.value.id)
      game.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function allocateCapacity(allocations) {
    if (!game.value) return
    loading.value = true
    try {
      const res = await gamesApi.allocate(game.value.id, allocations)
      game.value = res.data
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function applyMemberAssignments() {
    const allocs = Object.entries(pendingAllocations.value)
      .filter(([, { points }]) => points > 0)
      .map(([card_id, { points }]) => ({ card_id, points }))
    if (!allocs.length) return
    await allocateCapacity(allocs)
    clearAssignments()
  }

  async function moveCard(cardId, targetColumn) {
    if (!game.value) return null
    loading.value = true
    error.value = null
    try {
      const res = await gamesApi.moveCard(game.value.id, cardId, targetColumn)
      game.value = res.data
      return null
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      error.value = msg
      return msg
    } finally {
      loading.value = false
    }
  }

  async function endDay() {
    if (!game.value) return
    loading.value = true
    try {
      const res = await gamesApi.endDay(game.value.id)
      game.value = res.data
      clearAssignments()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  return {
    game, loading, error,
    cardsByColumn, todayEvent, isGameOver,
    teamCapacity, capacityRemaining, wipCounts,
    members, memberAssignments, pendingAllocations, hasAssignments,
    currentDragMember,
    getContribution, assignMember, unassignMember, clearAssignments, applyMemberAssignments,
    loadGame, resolveEvent, allocateCapacity, moveCard, endDay,
  }
})
