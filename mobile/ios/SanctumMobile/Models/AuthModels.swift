import Foundation

// Field names match the FastAPI backend (snake_case) so we can decode
// straight into these types without a custom CodingKeys map.

enum UserRole: String, Codable {
    case therapist
    case psychiatrist
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct SignupRequest: Encodable {
    let email: String
    let password: String
    let first_name: String
    let last_name: String
    let role: UserRole
}

struct AuthResponse: Decodable {
    let access_token: String
    let token_type: String
    let role: UserRole
    let first_name: String
    let last_name: String
}
