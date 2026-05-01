import Foundation

// Read-only JWT helper. We only ever need to inspect the subject claim —
// never to verify or sign, since the server already validates every
// request. So no crypto: just split on '.' and base64url-decode the
// middle segment.
enum JWTDecoder {
    static func subject(of token: String) -> String? {
        claims(of: token)?["sub"] as? String
    }

    private static func claims(of token: String) -> [String: Any]? {
        let parts = token.split(separator: ".")
        guard parts.count >= 2 else { return nil }
        let payload = String(parts[1])
        guard let data = base64URLDecode(payload),
              let json = try? JSONSerialization.jsonObject(with: data),
              let dict = json as? [String: Any] else {
            return nil
        }
        return dict
    }

    // JWT uses base64url (RFC 4648 §5): URL-safe alphabet, no padding.
    // Foundation's Data(base64Encoded:) needs '+' / '/' / padding to '='.
    private static func base64URLDecode(_ s: String) -> Data? {
        var b = s
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        while b.count % 4 != 0 { b.append("=") }
        return Data(base64Encoded: b)
    }
}
