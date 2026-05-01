import Foundation

// Mirrors the enriched response from GET /clients. The backend returns
// shared_with as either null or an inline psychiatrist object — the
// optional Psychiatrist below maps directly to that shape.

struct Client: Decodable, Identifiable, Hashable {
    let id: Int
    let first_name: String
    let last_name: String
    let shared_with: Psychiatrist?

    var fullName: String { "\(first_name) \(last_name)" }

    /// Returns a copy with the share state changed. Avoids manual
    /// reconstruction at every call site (and silently dropping new
    /// fields when the model grows).
    func with(sharedWith: Psychiatrist?) -> Client {
        Client(id: id, first_name: first_name, last_name: last_name, shared_with: sharedWith)
    }
}

struct ClientCreate: Encodable {
    let first_name: String
    let last_name: String
}
