import Foundation

// One type for both lookup-by-email (GET /auth/psychiatrists/{email}) and
// the shared_with field on a Client. Wire shape is identical, so a single
// model is the honest representation.
struct Psychiatrist: Codable, Hashable {
    let email: String
    let first_name: String
    let last_name: String

    var fullName: String {
        "\(first_name) \(last_name)".trimmingCharacters(in: .whitespaces)
    }
}

struct ShareRequest: Encodable {
    let psychiatrist_email: String
}

// POST /clients/{id}/share returns a confirmation message we don't use,
// but APIClient's generic needs a Decodable.
struct ShareResponse: Decodable {
    let message: String
}
