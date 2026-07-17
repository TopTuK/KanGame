// Shared helpers for the card-drag e2e suite.

export async function forceEnglishLocale(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('kangame-locale', 'en')
  })
}

export async function createGame(request, namePrefix = 'E2E') {
  const res = await request.post('/api/games', {
    data: { name: `${namePrefix} ${Date.now()}`, player_name: 'E2E Bot' },
  })
  if (!res.ok()) {
    throw new Error(`create game failed: ${res.status()} ${await res.text()}`)
  }
  return res.json()
}

export async function openGame(page, request) {
  const game = await createGame(request)
  await forceEnglishLocale(page)
  await page.goto(`/game/${game.id}`)

  // Every freshly created game starts on Day 9 with no metrics yet, so the
  // welcome modal always shows. Use a locator action (not .count()) so
  // Playwright auto-waits for it instead of racing loadGame()'s async fetch.
  await page.getByRole('button', { name: "Let's play!" }).click()
  return game
}

// The KanbanCard root element that contains the given card key (e.g. "S8").
export function cardContainer(page, cardKey) {
  return page.locator('.rounded-lg').filter({ has: page.locator(`text="${cardKey}"`) })
}

// The drop-target container for a given column key (e.g. "ready") — see the
// `data-column` attribute on KanbanColumn.vue's card-list div.
export function columnBody(page, columnKey) {
  return page.locator(`[data-column="${columnKey}"]`)
}

// Drags the card identified by cardKey onto targetLocator by dispatching the
// native HTML5 DragEvent sequence directly (dragstart/dragenter/dragover/drop/
// dragend) with a shared DataTransfer, rather than simulating physical mouse
// movement. Chromium's synthetic mouse-based drag simulation is unreliable
// for repeated drags within a single test (later drags in a sequence
// silently no-op); dispatching the events directly is deterministic and is
// Playwright's documented approach for native drag-and-drop.
export async function dragCardTo(page, cardKey, targetLocator) {
  const source = cardContainer(page, cardKey)
  const dataTransfer = await page.evaluateHandle(() => new DataTransfer())

  await source.dispatchEvent('dragstart', { dataTransfer })
  await targetLocator.dispatchEvent('dragenter', { dataTransfer })
  await targetLocator.dispatchEvent('dragover', { dataTransfer })
  await targetLocator.dispatchEvent('drop', { dataTransfer })
  await source.dispatchEvent('dragend', { dataTransfer })
}
