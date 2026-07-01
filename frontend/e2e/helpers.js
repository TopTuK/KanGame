// Shared helpers for the backlog-pull e2e suite.

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

  const startBtn = page.getByRole('button', { name: "Let's play!" })
  if (await startBtn.count()) {
    await startBtn.click()
  }
  return game
}

// The KanbanCard root element that contains the given card key (e.g. "S8").
export function cardContainer(page, cardKey) {
  return page.locator('.rounded-lg').filter({ has: page.locator(`text="${cardKey}"`) })
}

export function backlogTypeButton(page, label) {
  return page.getByRole('button', { name: new RegExp(`^${label} \\(\\d+\\) →$`) })
}

export function readyBacklogCount(button) {
  return button.textContent().then((text) => {
    const match = text.match(/\((\d+)\)/)
    return match ? Number(match[1]) : null
  })
}
