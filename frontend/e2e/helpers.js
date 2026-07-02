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

// Drags the card identified by cardKey onto targetLocator via a real native
// mouse down/move/up sequence, which reliably triggers HTML5
// dragstart/dragover/drop events in headless Chromium.
export async function dragCardTo(page, cardKey, targetLocator, { steps = 12 } = {}) {
  const source = cardContainer(page, cardKey)
  const sourceBox = await source.boundingBox()
  const targetBox = await targetLocator.boundingBox()
  const startX = sourceBox.x + sourceBox.width / 2
  const startY = sourceBox.y + sourceBox.height / 2
  await page.mouse.move(startX, startY)
  await page.mouse.down()
  // A small initial nudge is required to cross the browser's native
  // drag-initiation threshold before jumping to the actual target.
  await page.mouse.move(startX + 5, startY + 5, { steps: 5 })
  await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, { steps })
  await page.mouse.up()
}
