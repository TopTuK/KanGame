import { test, expect } from '@playwright/test'
import { openGame, cardContainer, columnBody, dragCardTo } from './helpers.js'

// Every new game starts on Day 9 with Ready already at its WIP limit (5/5)
// and the Analysis lane (analysis + analysis_done) at its limit (3/3) —
// see INITIAL_BOARD in backend/app/data/cards.py.

test('dragging into a full WIP column is rejected', async ({ page, request }) => {
  await openGame(page, request)

  const readyBefore = await columnBody(page, 'ready').locator('.rounded-lg').count()

  // S14 is the oldest Standard card in the Backlog; Ready is already 5/5.
  await dragCardTo(page, 'S14', columnBody(page, 'ready'))

  await expect(columnBody(page, 'backlog').locator('text="S14"')).toBeVisible()
  expect(await columnBody(page, 'ready').locator('.rounded-lg').count()).toBe(readyBefore)
})

test('dragging a card into its next column moves it forward', async ({ page, request }) => {
  await openGame(page, request)

  // Free Analysis WIP: drag the Analysis Done card (S8) forward into Development.
  await dragCardTo(page, 'S8', columnBody(page, 'development'))
  await expect(columnBody(page, 'development').locator('text="S8"')).toBeVisible()

  // Free Ready WIP: drag a Ready card (S11) forward into Analysis (now has room).
  await dragCardTo(page, 'S11', columnBody(page, 'analysis'))
  await expect(columnBody(page, 'analysis').locator('text="S11"')).toBeVisible()

  const readyBefore = await columnBody(page, 'ready').locator('.rounded-lg').count()

  await dragCardTo(page, 'S14', columnBody(page, 'ready'))

  await expect(columnBody(page, 'ready').locator('text="S14"')).toBeVisible()
  expect(await columnBody(page, 'ready').locator('.rounded-lg').count()).toBe(readyBefore + 1)
})

test('dragging a specific backlog card moves exactly that card, not the oldest of its type', async ({ page, request }) => {
  await openGame(page, request)

  // Free WIP the same way as above. Wait for each drop's API round-trip to
  // resolve (store.loading clears) before starting the next drag, since a
  // card only stays draggable while the store isn't mid-request.
  await dragCardTo(page, 'S8', columnBody(page, 'development'))
  await expect(columnBody(page, 'development').locator('text="S8"')).toBeVisible()
  await dragCardTo(page, 'S11', columnBody(page, 'analysis'))
  await expect(columnBody(page, 'analysis').locator('text="S11"')).toBeVisible()

  // S14 is the oldest Standard backlog card; deliberately drag a later one (S16) instead.
  await dragCardTo(page, 'S16', columnBody(page, 'ready'))

  await expect(columnBody(page, 'ready').locator('text="S16"')).toBeVisible()
  await expect(columnBody(page, 'backlog').locator('text="S14"')).toBeVisible()
})
