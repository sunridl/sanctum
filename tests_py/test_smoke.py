from playwright.sync_api import Page, expect


def test_homepage_loads(page: Page):
    page.goto("http://localhost:5173")
    expect(page).not_to_have_title("")

def test_psychiatrist_user_fixture_creates_and_tears_down(psychiatrist_user):
    assert psychiatrist_user["email"].startswith("psych-")
    assert psychiatrist_user["role"] == "psychiatrist"
    assert "@test.sanctum.com" in psychiatrist_user["email"]

def test_psychiatrist_can_log_in(page, psychiatrist_user):
    page.goto("http://localhost:5173/")

    page.get_by_placeholder("Email").fill(psychiatrist_user["email"])
    page.get_by_placeholder("Password").fill(psychiatrist_user["password"])
    page.get_by_role("button", name="Login").click()

    expect(page.get_by_text("Welcome, psychiatrist")).to_be_visible()