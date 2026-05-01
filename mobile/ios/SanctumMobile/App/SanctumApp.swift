import SwiftUI

@main
struct SanctumApp: App {
    init() {
        AppLaunchOptions.applyAtStartup()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}
