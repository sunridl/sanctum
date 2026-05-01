import Foundation

// Single source of truth for the API origin. Reads from UserDefaults so
// the value the user sets in the in-app Settings screen survives relaunch,
// and is overridable at launch via the -baseURL argument (see
// AppLaunchOptions). Default points at the local FastAPI dev server.
enum BaseURLProvider {
    private static let key = "sanctum.baseURL"
    static let defaultURL = "http://localhost:8000"

    static var currentString: String {
        UserDefaults.standard.string(forKey: key) ?? defaultURL
    }

    static var current: URL {
        URL(string: currentString) ?? URL(string: defaultURL)!
    }

    static func set(_ urlString: String) {
        UserDefaults.standard.set(urlString, forKey: key)
    }

    static func reset() {
        UserDefaults.standard.removeObject(forKey: key)
    }
}
