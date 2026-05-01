import Foundation

enum NotesService {
    static func list(clientId: Int, token: String) async throws -> [Note] {
        try await APIClient.shared.request(
            path: "/clients/\(clientId)/notes",
            method: "GET",
            token: token
        )
    }

    static func create(clientId: Int, data: NoteCreate, token: String) async throws -> Note {
        try await APIClient.shared.request(
            path: "/clients/\(clientId)/notes",
            method: "POST",
            body: data,
            token: token
        )
    }
}
