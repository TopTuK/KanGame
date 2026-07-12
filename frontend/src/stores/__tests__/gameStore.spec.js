import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../services/api.js', () => ({
  gamesApi: {
    list: vi.fn(),
    create: vi.fn(),
    get: vi.fn(),
    assignWorker: vi.fn(),
    pullCard: vi.fn(),
    startWork: vi.fn(),
    endDay: vi.fn(),
  },
}))

import { gamesApi } from '../../services/api.js'
import { useGameStore } from '../gameStore.js'

function makeWorker(overrides = {}) {
  return { id: 'a1', type: 'analyst', active: true, assigned_card_id: null, ...overrides }
}

function makeCard(overrides = {}) {
  return {
    id: 'card-1', card_key: 'S1', column: 'analysis', val: 1000, sort_order: 0,
    card_type: 'standard', ...overrides,
  }
}

function makeGame(overrides = {}) {
  return {
    id: 'game-1',
    status: 'active',
    phase: 'planning',
    work_done: false,
    wip_limits: { ready: 5, analysis: 3, development: 5, test: 3, expedite: 1 },
    team_config: { workers: [], buffs: {} },
    cards: [],
    ...overrides,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// --- computed: cardsByColumn / wipCounts / isGameOver / workers -----------

describe('cardsByColumn', () => {
  it('is empty before a game is loaded', () => {
    const store = useGameStore()
    expect(store.cardsByColumn).toEqual({})
  })

  it('groups cards by column', () => {
    const store = useGameStore()
    store.game = makeGame({
      cards: [makeCard({ id: 'c1', column: 'test' }), makeCard({ id: 'c2', column: 'ready' })],
    })
    expect(store.cardsByColumn.test.map(c => c.id)).toEqual(['c1'])
    expect(store.cardsByColumn.ready.map(c => c.id)).toEqual(['c2'])
    expect(store.cardsByColumn.development).toEqual([])
  })

  it('sorts backlog and exp_backlog by value descending (highest priority first)', () => {
    const store = useGameStore()
    store.game = makeGame({
      cards: [
        makeCard({ id: 'low', column: 'backlog', val: 4000 }),
        makeCard({ id: 'high', column: 'backlog', val: 9000 }),
        makeCard({ id: 'mid', column: 'backlog', val: 6000 }),
      ],
    })
    expect(store.cardsByColumn.backlog.map(c => c.id)).toEqual(['high', 'mid', 'low'])
  })

  it('sorts other columns by sort_order ascending', () => {
    const store = useGameStore()
    store.game = makeGame({
      cards: [
        makeCard({ id: 'second', column: 'test', sort_order: 2 }),
        makeCard({ id: 'first', column: 'test', sort_order: 0 }),
      ],
    })
    expect(store.cardsByColumn.test.map(c => c.id)).toEqual(['first', 'second'])
  })
})

describe('wipCounts', () => {
  it('is empty before a game is loaded', () => {
    const store = useGameStore()
    expect(store.wipCounts).toEqual({})
  })

  it('groups "done" lanes with their active-work counterpart, mirroring the backend', () => {
    const store = useGameStore()
    store.game = makeGame({
      cards: [
        makeCard({ id: 'c1', column: 'development' }),
        makeCard({ id: 'c2', column: 'dev_done' }),
        makeCard({ id: 'c3', column: 'ready' }),
      ],
    })
    expect(store.wipCounts.development).toBe(2)
    expect(store.wipCounts.ready).toBe(1)
    expect(store.wipCounts.test).toBe(0)
  })
})

describe('isGameOver', () => {
  it('is true only when game status is completed', () => {
    const store = useGameStore()
    expect(store.isGameOver).toBe(false)
    store.game = makeGame({ status: 'completed' })
    expect(store.isGameOver).toBe(true)
  })
})

describe('assignedWorkersByCard', () => {
  it('groups active assignments by card id', () => {
    const store = useGameStore()
    store.game = makeGame({
      team_config: {
        workers: [
          makeWorker({ id: 'a1', assigned_card_id: 'card-1' }),
          makeWorker({ id: 'd1', type: 'developer', assigned_card_id: 'card-1' }),
          makeWorker({ id: 'a2', assigned_card_id: null }),
        ],
        buffs: {},
      },
    })
    expect(store.assignedWorkersByCard['card-1'].map(w => w.id)).toEqual(['a1', 'd1'])
    expect(store.assignedWorkersByCard['card-2']).toBeUndefined()
  })
})

// --- column classification helpers -----------------------------------

describe('column classification', () => {
  const store = () => useGameStore()

  it('isPullableColumn recognizes "done" and "ready" lanes only', () => {
    const s = store()
    expect(s.isPullableColumn('ready')).toBe(true)
    expect(s.isPullableColumn('analysis_done')).toBe(true)
    expect(s.isPullableColumn('exp_test_done')).toBe(true)
    expect(s.isPullableColumn('analysis')).toBe(false)
    expect(s.isPullableColumn('backlog')).toBe(false)
  })

  it('isActiveWorkColumn recognizes analysis/development/test lanes (standard and expedite)', () => {
    const s = store()
    expect(s.isActiveWorkColumn('development')).toBe(true)
    expect(s.isActiveWorkColumn('exp_test')).toBe(true)
    expect(s.isActiveWorkColumn('ready')).toBe(false)
    expect(s.isActiveWorkColumn('deployed')).toBe(false)
  })

  it('isDraggableCardColumn recognizes pullable lanes plus the two backlogs', () => {
    const s = store()
    expect(s.isDraggableCardColumn('backlog')).toBe(true)
    expect(s.isDraggableCardColumn('exp_backlog')).toBe(true)
    expect(s.isDraggableCardColumn('ready')).toBe(true)
    expect(s.isDraggableCardColumn('analysis')).toBe(false)
    expect(s.isDraggableCardColumn('deployed')).toBe(false)
  })
})

// --- planning-phase gating -----------------------------------

describe('canPlan', () => {
  it('is true only during the planning phase before work is done', () => {
    const store = useGameStore()
    store.game = makeGame({ phase: 'planning', work_done: false })
    expect(store.canPlan()).toBe(true)

    store.game = makeGame({ phase: 'planning', work_done: true })
    expect(store.canPlan()).toBe(false)

    store.game = makeGame({ phase: 'completed', work_done: false })
    expect(store.canPlan()).toBe(false)
  })
})

describe('canPullCard', () => {
  it('is false outside the planning phase', () => {
    const store = useGameStore()
    store.game = makeGame({ work_done: true })
    expect(store.canPullCard('ready')) .toBe(false)
  })

  it('is false while a request is already loading', () => {
    const store = useGameStore()
    store.game = makeGame()
    store.loading = true
    expect(store.canPullCard('ready')).toBe(false)
  })

  it('allows the move when under the WIP limit and blocks it at the limit', () => {
    const store = useGameStore()
    store.game = makeGame({
      wip_limits: { ready: 2, analysis: 3, development: 5, test: 3, expedite: 1 },
      cards: [makeCard({ id: 'c1', column: 'ready' })],
    })
    expect(store.canPullCard('backlog')).toBe(true) // 1 of 2 ready slots used

    store.game.cards.push(makeCard({ id: 'c2', column: 'ready' }))
    expect(store.canPullCard('backlog')).toBe(false) // now at the limit
  })

  it('allows the move unconditionally when the source column has no WIP gate', () => {
    const store = useGameStore()
    store.game = makeGame({ wip_limits: {} })
    expect(store.canPullCard('test_done')).toBe(true) // test_done -> deployed is ungated
  })
})

describe('canDropOnColumn', () => {
  it('is false when nothing is being dragged', () => {
    const store = useGameStore()
    store.game = makeGame()
    expect(store.canDropOnColumn('ready')).toBe(false)
  })

  it('is false when the target does not match the drag target column', () => {
    const store = useGameStore()
    store.game = makeGame({ phase: 'planning', work_done: false })
    store.startDragCard('c1', 'backlog') // -> toColumn 'ready'
    expect(store.canDropOnColumn('analysis')).toBe(false)
  })

  it('applies the same WIP gate as canPullCard for the matching target', () => {
    const store = useGameStore()
    store.game = makeGame({
      wip_limits: { ready: 1, analysis: 3, development: 5, test: 3, expedite: 1 },
      cards: [makeCard({ id: 'blocker', column: 'ready' })],
    })
    store.startDragCard('c1', 'backlog') // -> toColumn 'ready', already at limit 1
    expect(store.canDropOnColumn('ready')).toBe(false)
  })
})

describe('startDragCard / stopDragCard', () => {
  it('sets the next column for a valid drag source during planning', () => {
    const store = useGameStore()
    store.game = makeGame({ phase: 'planning', work_done: false })
    store.startDragCard('c1', 'analysis_done')
    expect(store.draggingCard).toEqual({ id: 'c1', fromColumn: 'analysis_done', toColumn: 'development' })
  })

  it('resolves the expedite lane order independently from the standard lane', () => {
    const store = useGameStore()
    store.game = makeGame({ phase: 'planning', work_done: false })
    store.startDragCard('c1', 'exp_ready')
    expect(store.draggingCard.toColumn).toBe('exp_analysis')
  })

  it('does nothing outside the planning phase', () => {
    const store = useGameStore()
    store.game = makeGame({ work_done: true })
    store.startDragCard('c1', 'ready')
    expect(store.draggingCard).toBeNull()
  })

  it('does nothing for a non-draggable source column', () => {
    const store = useGameStore()
    store.game = makeGame({ phase: 'planning', work_done: false })
    store.startDragCard('c1', 'analysis')
    expect(store.draggingCard).toBeNull()
  })

  it('stopDragCard clears the drag state', () => {
    const store = useGameStore()
    store.game = makeGame({ phase: 'planning', work_done: false })
    store.startDragCard('c1', 'ready')
    store.stopDragCard()
    expect(store.draggingCard).toBeNull()
  })
})

// --- worker selection -----------------------------------

describe('selectWorker', () => {
  it('toggles an active, unassigned worker in and out of the selection', () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1' })], buffs: {} } })
    store.selectWorker('a1')
    expect(store.selectedWorkerIds).toEqual(['a1'])
    store.selectWorker('a1')
    expect(store.selectedWorkerIds).toEqual([])
  })

  it('ignores an inactive worker', () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1', active: false })], buffs: {} } })
    store.selectWorker('a1')
    expect(store.selectedWorkerIds).toEqual([])
  })

  it('ignores a worker already assigned to a card', () => {
    const store = useGameStore()
    store.game = makeGame({
      team_config: { workers: [makeWorker({ id: 'a1', assigned_card_id: 'card-1' })], buffs: {} },
    })
    store.selectWorker('a1')
    expect(store.selectedWorkerIds).toEqual([])
  })

  it('does nothing outside the planning phase', () => {
    const store = useGameStore()
    store.game = makeGame({ work_done: true, team_config: { workers: [makeWorker()], buffs: {} } })
    store.selectWorker('a1')
    expect(store.selectedWorkerIds).toEqual([])
  })
})

describe('startDragWorker / stopDragWorker', () => {
  it('sets the dragging worker and clears the current selection', () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1' })], buffs: {} } })
    store.selectWorker('a1')
    store.startDragWorker('a1')
    expect(store.draggingWorkerId).toBe('a1')
    expect(store.selectedWorkerIds).toEqual([])
  })

  it('ignores an inactive worker', () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1', active: false })], buffs: {} } })
    store.startDragWorker('a1')
    expect(store.draggingWorkerId).toBeNull()
  })

  it('stopDragWorker clears the dragging worker', () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1' })], buffs: {} } })
    store.startDragWorker('a1')
    store.stopDragWorker()
    expect(store.draggingWorkerId).toBeNull()
  })
})

// --- async actions -----------------------------------

describe('assignWorker', () => {
  it('does nothing while another request is loading', async () => {
    const store = useGameStore()
    store.game = makeGame()
    store.loading = true
    await store.assignWorker('a1', 'card-1')
    expect(gamesApi.assignWorker).not.toHaveBeenCalled()
  })

  it('replaces the game state on success and clears the dragging worker', async () => {
    const store = useGameStore()
    store.game = makeGame()
    store.draggingWorkerId = 'a1'
    const updatedGame = makeGame({ id: 'game-1', phase: 'planning' })
    gamesApi.assignWorker.mockResolvedValue({ data: updatedGame })

    await store.assignWorker('a1', 'card-1')

    expect(gamesApi.assignWorker).toHaveBeenCalledWith('game-1', 'a1', 'card-1')
    expect(store.game).toEqual(updatedGame)
    expect(store.draggingWorkerId).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('keeps the current selection when clearSelection is false', async () => {
    const store = useGameStore()
    store.game = makeGame()
    store.selectedWorkerIds = ['a1', 'a2']
    gamesApi.assignWorker.mockResolvedValue({ data: makeGame() })

    await store.assignWorker('a1', 'card-1', { clearSelection: false })

    expect(store.selectedWorkerIds).toEqual(['a1', 'a2'])
  })

  it('surfaces the backend error message on failure', async () => {
    const store = useGameStore()
    store.game = makeGame()
    gamesApi.assignWorker.mockRejectedValue({ response: { data: { detail: 'Assignment not allowed' } } })

    await store.assignWorker('a1', 'card-1')

    expect(store.error).toBe('Assignment not allowed')
    expect(store.loading).toBe(false)
  })
})

describe('unassignWorker', () => {
  it('does nothing when the worker has no assignment', async () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1', assigned_card_id: null })], buffs: {} } })
    await store.unassignWorker('a1')
    expect(gamesApi.assignWorker).not.toHaveBeenCalled()
  })

  it('re-assigns the worker to its current card, which the backend treats as a toggle-off', async () => {
    const store = useGameStore()
    store.game = makeGame({ team_config: { workers: [makeWorker({ id: 'a1', assigned_card_id: 'card-1' })], buffs: {} } })
    gamesApi.assignWorker.mockResolvedValue({ data: makeGame() })

    await store.unassignWorker('a1')

    expect(gamesApi.assignWorker).toHaveBeenCalledWith('game-1', 'a1', 'card-1')
  })
})

describe('assignToCard', () => {
  it('does nothing when no workers are selected', async () => {
    const store = useGameStore()
    store.game = makeGame()
    await store.assignToCard('card-1')
    expect(gamesApi.assignWorker).not.toHaveBeenCalled()
  })

  it('assigns every selected worker not already on the target card, and clears selection afterwards', async () => {
    const store = useGameStore()
    store.game = makeGame({
      team_config: {
        workers: [
          makeWorker({ id: 'a1', assigned_card_id: 'card-1' }), // already there -> skipped
          makeWorker({ id: 'a2', assigned_card_id: null }),
        ],
        buffs: {},
      },
    })
    store.selectedWorkerIds = ['a1', 'a2']
    gamesApi.assignWorker.mockResolvedValue({ data: makeGame() })

    await store.assignToCard('card-1')

    expect(gamesApi.assignWorker).toHaveBeenCalledTimes(1)
    expect(gamesApi.assignWorker).toHaveBeenCalledWith('game-1', 'a2', 'card-1')
    expect(store.selectedWorkerIds).toEqual([])
    expect(store.draggingWorkerId).toBeNull()
  })
})

describe('pullCard', () => {
  it('replaces the game state on success', async () => {
    const store = useGameStore()
    store.game = makeGame()
    const updatedGame = makeGame()
    gamesApi.pullCard.mockResolvedValue({ data: updatedGame })

    await store.pullCard('card-1')

    expect(gamesApi.pullCard).toHaveBeenCalledWith('game-1', 'card-1')
    expect(store.game).toEqual(updatedGame)
  })

  it('surfaces a WIP-limit error from the backend', async () => {
    const store = useGameStore()
    store.game = makeGame()
    gamesApi.pullCard.mockRejectedValue({ response: { data: { detail: 'WIP limit reached for ready' } } })

    await store.pullCard('card-1')

    expect(store.error).toBe('WIP limit reached for ready')
  })
})

describe('startWork', () => {
  it('stores the resulting game and work log, and opens the log modal', async () => {
    const store = useGameStore()
    store.game = makeGame()
    const updatedGame = makeGame({ work_done: true })
    gamesApi.startWork.mockResolvedValue({ data: { game: updatedGame, log: [{ type: 'work' }] } })

    await store.startWork()

    expect(store.game).toEqual(updatedGame)
    expect(store.workLog).toEqual([{ type: 'work' }])
    expect(store.showWorkLog).toBe(true)
  })
})

describe('endDay', () => {
  it('stores the resulting game and end-day modal, and closes the work log', async () => {
    const store = useGameStore()
    store.game = makeGame()
    store.showWorkLog = true
    store.workLog = [{ type: 'work' }]
    const updatedGame = makeGame({ current_day: 10 })
    gamesApi.endDay.mockResolvedValue({ data: { game: updatedGame, modal: { day: 9 } } })

    await store.endDay()

    expect(store.game).toEqual(updatedGame)
    expect(store.endDayModal).toEqual({ day: 9 })
    expect(store.showWorkLog).toBe(false)
    expect(store.workLog).toEqual([])
  })
})

describe('dismissEndDayModal / dismissWorkLog', () => {
  it('clears the end-day modal and the work-log flag', () => {
    const store = useGameStore()
    store.endDayModal = { day: 9 }
    store.showWorkLog = true

    store.dismissEndDayModal()
    store.dismissWorkLog()

    expect(store.endDayModal).toBeNull()
    expect(store.showWorkLog).toBe(false)
  })
})

describe('loadGame', () => {
  it('loads the game and clears any worker selection', async () => {
    const store = useGameStore()
    store.selectedWorkerIds = ['a1']
    const loadedGame = makeGame()
    gamesApi.get.mockResolvedValue({ data: loadedGame })

    await store.loadGame('game-1')

    expect(gamesApi.get).toHaveBeenCalledWith('game-1')
    expect(store.game).toEqual(loadedGame)
    expect(store.selectedWorkerIds).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('surfaces a network error', async () => {
    const store = useGameStore()
    gamesApi.get.mockRejectedValue(new Error('Network Error'))

    await store.loadGame('game-1')

    expect(store.error).toBe('Network Error')
  })
})
