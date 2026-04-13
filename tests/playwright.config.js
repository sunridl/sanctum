export default {
  reporter: [
    ['list'],
    ['allure-playwright']
  ],
  use: {
    baseURL: 'http://localhost:5173',
  }
}