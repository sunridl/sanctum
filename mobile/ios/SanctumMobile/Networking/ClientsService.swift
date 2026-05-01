import Foundation

// Wraps the /clients API surface. Holding the auth token at the call site
// (rather than as a stored property) means the service has no lifecycle of
// its own — it's a thin function namespace, easy to use and easy to mock
// at test time.
enum ClientsService {
    static func list(token: String) async throws -> [Client] {
        try await APIClient.shared.request(
            path: "/clients/",
            method: "GET",
            token: token
        )
    }

    static func create(_ data: ClientCreate, token: String) async throws -> Client {
        // The backend's POST /clients returns a non-enriched record
        // (no shared_with field as an object — just null). The Client
        // decoder treats shared_with as optional, so this still decodes.
        try await APIClient.shared.request(
            path: "/clients/",
            method: "POST",
            body: data,
            token: token
        )
    }

    static func delete(id: Int, token: String) async throws {
        let _: EmptyResponse = try await APIClient.shared.request(
            path: "/clients/\(id)",
            method: "DELETE",
            token: token
        )
    }
}
