import { test, expect } from '@playwright/test'

test('therapist can login and see clients', async ({ page }) => {
  await page.goto('http://localhost:5173')

  await page.fill('input[type="email"]', 'therapist@sanctum.com')
  await page.fill('input[type="password"]', 'secret123')
  await page.click('button[type="submit"]')

  await expect(page.locator('strong')).toHaveText('therapist')
  await expect(page.locator('ul')).toContainText('Carol')
  await expect(page.locator('ul')).toContainText('David')

  await page.click('button:has-text("Logout")')

  await expect(page.locator('input[type="email"]')).toBeVisible()
})

test('login fails with wrong password', async ({ page }) => {
  await page.goto('http://localhost:5173')

  await page.fill('input[type="email"]', 'therapist@sanctum.com')
  await page.fill('input[type="password"]', 'wrongpassword')
  await page.click('button[type="submit"]')

  await expect(page.locator('input[type="email"]')).toBeVisible()
  await expect(page.locator('strong')).not.toBeVisible()
})

test('psychiatrist sees shared clients only', async ({ page }) => {
  await page.goto('http://localhost:5173')

  await page.fill('input[type="email"]', 'psych@sanctum.com')
  await page.fill('input[type="password"]', 'secret123')
  await page.click('button[type="submit"]')

  await expect(page.locator('strong')).toHaveText('psychiatrist')
  await expect(page.locator('ul')).not.toContainText('Carol')
  await expect(page.locator('ul')).not.toContainText('David')
})