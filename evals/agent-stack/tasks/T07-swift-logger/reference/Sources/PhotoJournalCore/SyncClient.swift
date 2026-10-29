import Foundation

public enum SyncError: Error, Equatable {
    case transport(String)
    case rejected(Int)
}

public final class SyncClient {
    public typealias Transport = (_ endpoint: URL, _ body: Data) throws -> Int

    private let endpoint: URL
    private let transport: Transport

    public init(endpoint: URL, transport: @escaping Transport) {
        self.endpoint = endpoint
        self.transport = transport
    }

    public func push(_ entries: [JournalEntry]) throws {
        let body = try JSONEncoder().encode(entries)
        let status: Int
        do {
            status = try transport(endpoint, body)
        } catch {
            AppLogger.shared.error(
                "push to \(endpoint.host ?? "unknown host") failed: \(error)",
                category: .sync
            )
            throw SyncError.transport(error.localizedDescription)
        }
        guard (200..<300).contains(status) else {
            AppLogger.shared.error("push rejected with HTTP \(status)", category: .sync)
            throw SyncError.rejected(status)
        }
    }
}
