import Foundation
import Observation

// Single source of truth for session state. @MainActor because every
// mutation either runs from a SwiftUI view body (already main-isolated)
// or from a Task started by one — explicit isolation makes the data-race
// guarantees obvious to the compiler under strict concurrency.
@MainActor
@Observable
final class AuthStore {
    private(set) var token: String?
    private(set) var role: UserRole?
    private(set) var firstName: String = ""
    private(set) var lastName: String = ""

    var isLoggedIn: Bool { token != nil }

    // Token lives in Keychain (it's a credential). Profile fields live in
    // UserDefaults — they're not secrets, and storing them here means a
    // cold launch with a saved token can immediately render role-aware UI
    // without an extra round-trip to a /me endpoint (which the backend
    // doesn't have).
    private static let roleKey = "sanctum.profile.role"
    private static let firstNameKey = "sanctum.profile.firstName"
    private static let lastNameKey = "sanctum.profile.lastName"

    init() {
        if let saved = KeychainTokenStore.read() {
            self.token = saved
            let defaults = UserDefaults.standard
            if let raw = defaults.string(forKey: Self.roleKey) {
                self.role = UserRole(rawValue: raw)
            }
            self.firstName = defaults.string(forKey: Self.firstNameKey) ?? ""
            self.lastName = defaults.string(forKey: Self.lastNameKey) ?? ""
        }
    }

    var email: String? {
        // The JWT 'sub' claim is the user's email. Decoding the token here
        // means we don't need to persist email separately. Used by the
        // delete-account flow which targets DELETE /auth/users/{email}.
        guard let token else { return nil }
        return JWTDecoder.subject(of: token)
    }

    func login(email: String, password: String) async throws {
        let body = LoginRequest(email: email, password: password)
        let resp: AuthResponse = try await APIClient.shared.request(
            path: "/auth/login",
            method: "POST",
            body: body
        )
        apply(resp)
    }

    func signup(_ data: SignupRequest) async throws {
        let resp: AuthResponse = try await APIClient.shared.request(
            path: "/auth/signup",
            method: "POST",
            body: data
        )
        apply(resp)
    }

    func deleteAccount() async throws {
        guard let token, let email else { return }
        let _: EmptyResponse = try await APIClient.shared.request(
            path: "/auth/users/\(email)",
            method: "DELETE",
            token: token
        )
        // Clear local session — the server will reject any further calls
        // with this token (the user no longer exists in USERS).
        logout()
    }

    func logout() {
        try? KeychainTokenStore.clear()
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Self.roleKey)
        defaults.removeObject(forKey: Self.firstNameKey)
        defaults.removeObject(forKey: Self.lastNameKey)
        self.token = nil
        self.role = nil
        self.firstName = ""
        self.lastName = ""
    }

    private func persist(role: UserRole, firstName: String, lastName: String) {
        let defaults = UserDefaults.standard
        defaults.set(role.rawValue, forKey: Self.roleKey)
        defaults.set(firstName, forKey: Self.firstNameKey)
        defaults.set(lastName, forKey: Self.lastNameKey)
    }

    private func apply(_ resp: AuthResponse) {
        // try? not throw: a Keychain failure only loses the cold-launch
        // session restore — the in-memory session continues normally.
        try? KeychainTokenStore.save(token: resp.access_token)
        persist(role: resp.role, firstName: resp.first_name, lastName: resp.last_name)
        self.token = resp.access_token
        self.role = resp.role
        self.firstName = resp.first_name
        self.lastName = resp.last_name
    }
}
