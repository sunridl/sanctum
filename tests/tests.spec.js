import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/LoginPage.js'
import { DashboardPage } from './pages/DashboardPage.js'

test('therapist can login and see clients', async ({ page }) => {
  const loginPage = new LoginPage(page)
  const dashboard = new DashboardPage(page)

  await loginPage.goto()
  await loginPage.loginAs('therapist@sanctum.com', 'secret123')

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
  await loginPage.loginAs('therapist@sanctum.com', 'wrongpassword')

  await expect(loginPage.emailInput).toBeVisible()
  await expect(dashboard.roleLabel).not.toBeVisible()
})

test('psychiatrist sees shared clients only', async ({ page }) => {
  const loginPage = new LoginPage(page)
  const dashboard = new DashboardPage(page)

  await loginPage.goto()
  await loginPage.loginAs('psych@sanctum.com', 'secret123')

  await expect(dashboard.roleLabel).toHaveText('psychiatrist')
  await expect(dashboard.clientList).not.toContainText('Carol')
  await expect(dashboard.clientList).not.toContainText('David')
})