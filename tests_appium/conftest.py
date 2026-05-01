"""Pytest fixtures for the Sanctum iOS Appium suite.

Connects to an already-running Appium server (default http://127.0.0.1:4723)
and drives the iOS app already installed on a booted simulator.

Tunables via environment variables:
- APPIUM_URL   server URL (default: http://127.0.0.1:4723)
- SIM_UDID     target simulator UDID (default: the booted "Appium" sim)
- BACKEND_URL  base URL the app will hit (default: http://localhost:8000)
- BUNDLE_ID    app bundle identifier (default: com.sanctum.mobile)
"""
import os
import uuid

import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions

import api_helpers

APPIUM_URL = os.environ.get("APPIUM_URL", "http://127.0.0.1:4723")
SIM_UDID = os.environ.get("SIM_UDID", "A97F0A0B-61C8-41D2-BCD2-905BD95B6418")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BUNDLE_ID = os.environ.get("BUNDLE_ID", "com.sanctum.mobile")


@pytest.fixture
def driver():
    """Function-scoped driver: each test gets a fresh launch with cleared
    state, so test order can never leak through Keychain or UserDefaults.
    The cost (~2-3s per test for app launch) is worth the isolation
    until the suite is large enough that we revisit it."""
    opts = XCUITestOptions()
    opts.platform_name = "iOS"
    opts.automation_name = "XCUITest"
    opts.udid = SIM_UDID
    opts.bundle_id = BUNDLE_ID
    # noReset=True keeps the installed app — we don't want to reinstall
    # every test. State is wiped via -resetState instead, which is faster
    # and keyed off the app's own launch-arg parsing.
    opts.no_reset = True
    # Without these two, Appium reuses the already-running app instance
    # and our -resetState arg never reaches AppLaunchOptions (init() only
    # runs at fresh launch). Forcing terminate + relaunch per session is
    # what makes state-isolation reliable.
    opts.force_app_launch = True
    opts.should_terminate_app = True
    # Hardware keyboard ON, software keyboard suppressed: the on-screen
    # keyboard otherwise hides the bottom of tall forms (signup) and
    # makes elements report not-displayed even when they exist. Native
    # XCUITest typing still works because send_keys injects characters
    # directly into the focused field — no keyboard required.
    opts.connect_hardware_keyboard = True
    opts.set_capability("appium:forceSimulatorSoftwareKeyboardPresence", False)
    opts.process_arguments = {
        "args": ["-resetState", "YES", "-baseURL", BACKEND_URL]
    }

    drv = webdriver.Remote(APPIUM_URL, options=opts)
    drv.implicitly_wait(0)  # Be explicit about waits in page objects.
    try:
        yield drv
    finally:
        drv.quit()


# ---------------------------------------------------------------------------
# Backend-state fixtures
# ---------------------------------------------------------------------------
# These talk to the FastAPI backend directly so tests don't depend on which
# users/clients happen to be in the seed data. Each test that needs a
# client gets a freshly-created one and a finalizer that removes it
# (cascading shares + orphan-tagging notes per the backend's delete logic).


@pytest.fixture
def therapist_token() -> str:
    return api_helpers.get_token(api_helpers.THERAPIST_EMAIL, api_helpers.THERAPIST_PASSWORD)


@pytest.fixture
def psych_token() -> str:
    return api_helpers.get_token(api_helpers.PSYCH_EMAIL, api_helpers.PSYCH_PASSWORD)


@pytest.fixture
def seeded_client(therapist_token, request) -> dict:
    """Create a client owned by the seeded therapist and return its
    {id, first_name, last_name}. The finalizer removes it so the backend
    state is identical at the start and end of every test."""
    suffix = uuid.uuid4().hex[:6]
    first_name, last_name = f"Test{suffix}", "Client"
    client = api_helpers.create_client(first_name, last_name, therapist_token)

    def cleanup():
        api_helpers.delete_client(client["id"], therapist_token)

    request.addfinalizer(cleanup)
    return client


@pytest.fixture
def unique_client_names(request, therapist_token):
    """Generate a unique (first_name, last_name) for tests that create the
    client themselves through the UI. Cleanup looks the client up by name
    after the test and deletes it via the backend."""
    suffix = uuid.uuid4().hex[:6]
    first_name, last_name = f"Test{suffix}", "Client"

    def cleanup():
        cid = api_helpers.find_client_id(therapist_token, first_name, last_name)
        if cid is not None:
            api_helpers.delete_client(cid, therapist_token)

    request.addfinalizer(cleanup)
    return first_name, last_name
