import Foundation

// Launch-time switches an Appium suite (or manual tester) can pass to
// short-circuit setup. Keeping them in one place so the contract is
// obvious from a single file.
//
//   -baseURL <url>     override BaseURLProvider for this run
//   -resetState YES    wipe Keychain + UserDefaults before launch
//   -seedToken <jwt>   pre-load an auth token (skip the login screen)
enum AppLaunchOptions {
    static func applyAtStartup() {
        let args = ProcessInfo.processInfo.arguments

        if value(for: "-resetState", in: args) == "YES" {
            if let bundleID = Bundle.main.bundleIdentifier {
                UserDefaults.standard.removePersistentDomain(forName: bundleID)
            }
            try? KeychainTokenStore.clear()
        }

        if let baseURL = value(for: "-baseURL", in: args) {
            BaseURLProvider.set(baseURL)
        }

        if let token = value(for: "-seedToken", in: args) {
            try? KeychainTokenStore.save(token: token)
        }
    }

    private static func value(for flag: String, in args: [String]) -> String? {
        guard let idx = args.firstIndex(of: flag), idx + 1 < args.count else {
            return nil
        }
        return args[idx + 1]
    }
}
