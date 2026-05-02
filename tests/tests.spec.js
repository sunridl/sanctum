import { test, expect, request } from '@playwright/test'
import { randomBytes } from 'crypto'
import { LoginPage } from './pages/LoginPage.js'
import { DashboardPage } from './pages/DashboardPage.js'

const BACKEND = 'http://localhost:8000'

// Test credentials are generated per Playwright run so they never appear
// in the repo. The beforeAll hook registers these accounts at session
// start and seeds the clients the original assertions reference (Carol,
// David). Domain is a fictional .io (not a reserved RFC-2606 TLD which
// Pydantic's EmailStr would reject).
const RUN_SUFFIX = randomBytes(4).toString('hex')
const THERAPIST = {
  email: `test-therapist-${RUN_SUFFIX}@sanctum-tests.io`,
  password: randomBytes(16).toString('base64url'),
}
const PSYCH = {
  email: `test-psych-${RUN_SUFFIX}@sanctum-tests.io`,
  password: randomBytes(16).toString('base64url'),
}

async function getToken(ctx, { email, password }) {
  const res = await ctx.post(`${BACKEND}/auth/login`, { data: { email, password } })
  return (await res.json()).access_token
}

test.beforeAll(async () => {
  const ctx = await request.newContext()

  await ctx.post(`${BACKEND}/auth/users`, {
    data: { ...THERAPIST, role: 'therapist', first_name: 'Sarah', last_name: 'Hill' },
  })
  await ctx.post(`${BACKEND}/auth/users`, {
    data: { ...PSYCH, role: 'psychiatrist', first_name: 'Pat', last_name: 'Chen' },
  })

  const token = await getToken(ctx, THERAPIST)
  for (const client of [
    { first_name: 'Carol', last_name: 'Smith' },
    { first_name: 'David', last_name: 'Jones' },
  ]) {
    await ctx.post(`${BACKEND}/clients/`, {
      data: client,
      headers: { Authorization: `Bearer ${token}` },
    })
  }

  await ctx.dispose()
})

test.afterAll(async () => {
  const ctx = await request.newContext()
  for (const acct of [THERAPIST, PSYCH]) {
    try {
      const token = await getToken(ctx, acct)
      await ctx.delete(`${BACKEND}/auth/users/${acct.email}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {
      // Account already gone (e.g. test deleted it) — fine.
    }
  }
  await ctx.dispose()
})

test('therapist can login and see clients', async ({ page }) => {
  const loginPage = new LoginPage(page)
  const dashboard = new DashboardPage(page)

  await loginPage.goto()
  await loginPage.loginAs(THERAPIST.email, THERAPIST.password)

  await expect(dashboard.roleLabel).toHaveText('therapist')
  await expect(dashboard.clientList).toContainText('Carol')
  await expect(dashboard.clientList).toContainText('David')

  await dashboard.logout()
  await expect(loginPage.emailInput).toBeVisible()
})

test('login fails with wrong password', async ({ page }) => {
  const loginPage = new LoginPage(page)
  const dashboard = new DashboardPage(page)

  await loginPage.goto()
  await loginPage.loginAs(THERAPIST.email, 'definitely-wrong-password')

  await expect(loginPage.emailInput).toBeVisible()
  await expect(dashboard.roleLabel).not.toBeVisible()
})

test('psychiatrist sees shared clients only', async ({ page }) => {
  const loginPage = new LoginPage(page)
  const dashboard = new DashboardPage(page)

  await loginPage.goto()
  await loginPage.loginAs(PSYCH.email, PSYCH.password)

  await expect(dashboard.roleLabel).toHaveText('psychiatrist')
  await expect(dashboard.clientList).not.toContainText('Carol')
  await expect(dashboard.clientList).not.toContainText('David')
})
