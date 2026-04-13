export class DashboardPage {
  constructor(page) {
    this.page = page
    this.roleLabel = page.locator('strong')
    this.clientList = page.locator('ul')
    this.logoutButton = page.locator('button:has-text("Logout")')
  }

  async logout() {
    await this.logoutButton.click()
  }
}