import Foundation

// Thin URLSession wrapper. Centralizes: base URL resolution, JSON encoding/
// decoding, Authorization header attachment, and error categorization.
// All other code should hit the API through here so retries/auth/baseURL
// concerns stay in one place.
struct APIClient {
    static let shared = APIClient()

    // Shared coders. Stateless, thread-safe, and re-using them avoids
    // per-request allocation. Becomes the place to centralize date or
    // key-decoding strategies if those are ever needed.
    private static let encoder = JSONEncoder()
    private static let decoder = JSONDecoder()

    enum APIError: Error {
        case invalidResponse
        case http(status: Int, body: Data)
        case decoding(Error)
        case transport(Error)
    }

    func request<Response: Decodable>(
        path: String,
        method: String = "GET",
        body: Encodable? = nil,
        token: String? = nil,
        as _: Response.Type = Response.self
    ) async throws -> Response {
        var url = BaseURLProvider.current
        url.append(path: path)

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")

        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body {
            req.httpBody = try Self.encoder.encode(AnyEncodable(body))
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: req)
        } catch {
            throw APIError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard 200..<300 ~= http.statusCode else {
            throw APIError.http(status: http.statusCode, body: data)
        }

        // 204 No Content endpoints (like DELETE) return an empty body —
        // skip decoding and hand back EmptyResponse if the caller asked for it.
        if Response.self == EmptyResponse.self {
            return EmptyResponse() as! Response
        }

        do {
            return try Self.decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }
}

struct EmptyResponse: Decodable {}

// JSONEncoder only encodes concrete types, but we want callers to pass
// any Encodable. This shim erases the type at the call boundary.
private struct AnyEncodable: Encodable {
    let value: Encodable
    init(_ value: Encodable) { self.value = value }
    func encode(to encoder: Encoder) throws { try value.encode(to: encoder) }
}
