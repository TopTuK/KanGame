import { test, expect } from '@playwright/test'
import { openGame, cardContainer, backlogTypeButton, readyBacklogCount } from './helpers.js'

// Every new game starts on Day 9 with Ready already at its WIP limit (5/5)
// and Analysis at its limit (3/3) — see INITIAL_BOARD in backend/app/data/cards.py.

test('backlog shows pull controls with live per-type counts', async ({ page, request }) => {
  await openGame(page, request)

  const standard = backlogTypeButton(page, 'Standard \\(S\\)')
  const fixed = backlogTypeButton(page, 'Fixed-date \\(F\\)')
  const intangible = backlogTypeButton(page, 'Intangible \\(I\\)')

  await expect(standard).toBeVisible()
  await expect(fixed).toBeVisible()
  await expect(intangible).toBeVisible()

  expect(await readyBacklogCount(standard)).toBeGreaterThan(0)
})

test('pulling from backlog is rejected while Ready is at its WIP limit', async ({ page, request }) => {
  await openGame(page, request)

  const standard = backlogTypeButton(page, 'Standard \\(S\\)')
  const countBefore = await readyBacklogCount(standard)

  await standard.click()

  await expect(page.getByText('Ready WIP limit reached (max 5)')).toBeVisible()
  expect(await readyBacklogCount(standard)).toBe(countBefore)
})

test('pulling from backlog moves a card into Ready once a slot frees up', async ({ page, request }) => {
  await openGame(page, request)

  // Free Analysis WIP: pull the Analysis Done card (S8) forward into Development.
  await cardContainer(page, 'S8').getByRole('button', { name: 'Pull →' }).click()

  // Free Ready WIP: pull a Ready card (S11) forward into Analysis (now has room).
  await cardContainer(page, 'S11').getByRole('button', { name: 'Pull →' }).click()

  const standard = backlogTypeButton(page, 'Standard \\(S\\)')
  const countBefore = await readyBacklogCount(standard)

  await standard.click()

  await expect(page.getByText('Ready WIP limit reached', { exact: false })).not.toBeVisible()
  expect(await readyBacklogCount(standard)).toBe(countBefore - 1)
})
