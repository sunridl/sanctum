import Foundation

// Mirrors the enriched response from GET /clients/{id}/notes — the backend
// joins the author's display name onto each note at read time.
struct Note: Decodable, Identifiable, Hashable {
    let id: Int
    let content: String
    let is_private: Bool
    let author: String
    let role: UserRole
    // Enriched only by the GET endpoint — POST responses omit these fields,
    // so they have to be optional or decoding the create-note response
    // would fail. Display falls back to the author email when missing.
    let author_first_name: String?
    let author_last_name: String?

    var authorDisplayName: String {
        let combined = "\(author_first_name ?? "") \(author_last_name ?? "")"
            .trimmingCharacters(in: .whitespaces)
        return combined.isEmpty ? author : combined
    }
}

struct NoteCreate: Encodable {
    let content: String
    let is_private: Bool
}
