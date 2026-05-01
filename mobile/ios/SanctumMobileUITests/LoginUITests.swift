import XCTest

// Baseline XCUITest sanity checks. These run in Xcode and prove the
// accessibility identifiers are wired up — same identifiers Appium will
// query later. If these break, Appium tests will break the same way.
final class LoginUITests: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    func testLoginScreenElementsAreReachable() {
        let app = XCUIApplication()
        app.launchArguments = ["-resetState", "YES"]
        app.launch()

        XCTAssertTrue(app.textFields["login.email"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.secureTextFields["login.password"].exists)
        XCTAssertTrue(app.buttons["login.submit"].exists)
    }

    func testLoginButtonDisabledWhenFieldsEmpty() {
        let app = XCUIApplication()
        app.launchArguments = ["-resetState", "YES"]
        app.launch()

        let submit = app.buttons["login.submit"]
        XCTAssertTrue(submit.waitForExistence(timeout: 5))
        XCTAssertFalse(submit.isEnabled)
    }
}
