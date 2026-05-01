import Foundation

enum SharingService {
    static func lookup(email: String, token: String) async throws -> Psychiatrist {
        // Trim + lowercase: the backend does a dict lookup, so any
        // whitespace or case variation the user types would 404.
        let normalized = email.trimmingCharacters(in: .whitespaces).lowercased()
        let encoded = normalized.addingPercentEncoding(
            withAllowedCharacters: .urlPathAllowed
        ) ?? normalized
        return try await APIClient.shared.request(
            path: "/auth/psychiatrists/\(encoded)",
            method: "GET",
            token: token
        )
    }

    static func share(clientId: Int, psychiatristEmail: String, token: String) async throws {
        let _: ShareResponse = try await APIClient.shared.request(
            path: "/clients/\(clientId)/share",
            method: "POST",
            body: ShareRequest(psychiatrist_email: psychiatristEmail),
            token: token
        )
    }

    static func unshare(clientId: Int, token: String) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            path: "/clients/\(clientId)/share",
            method: "DELETE",
            token: token
        )
    }
}
