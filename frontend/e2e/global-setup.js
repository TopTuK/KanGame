import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { request } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const STORAGE_STATE = path.join(__dirname, '.auth', 'state.json')

// Logs in via the ENABLE_TEST_LOGIN-gated backend endpoint (bypasses the real
// OIDC provider, which e2e tests have no way to drive) and saves the
// resulting session cookie for all tests to reuse.
export default async function globalSetup(config) {
  const baseURL = config.projects[0].use.baseURL
  const context = await request.newContext({ baseURL })

  const res = await context.post('/api/dev/test-login')
  if (!res.ok()) {
    await context.dispose()
    throw new Error(
      `Test login failed (${res.status()} ${await res.text()}).\n` +
      'Start the stack with test login enabled first:\n' +
      '  docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build'
    )
  }

  fs.mkdirSync(path.dirname(STORAGE_STATE), { recursive: true })
  await context.storageState({ path: STORAGE_STATE })
  await context.dispose()
}
