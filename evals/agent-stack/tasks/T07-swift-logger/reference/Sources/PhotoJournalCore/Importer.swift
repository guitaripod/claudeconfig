import Foundation

public enum ImporterError: Error, Equatable {
    case unreadable(String)
    case missingCreationDate(String)
}

public final class Importer {
    private let store: JournalStore

    public init(store: JournalStore) {
        self.store = store
    }

    public func importBatch(_ urls: [URL]) -> Int {
        var imported = 0
        for url in urls {
            do {
                store.add(try makeEntry(for: url))
                imported += 1
            } catch {
                AppLogger.shared.error("import of \(url.lastPathComponent) failed: \(error)", category: .importing)
            }
        }
        return imported
    }

    private func makeEntry(for url: URL) throws -> JournalEntry {
        guard FileManager.default.isReadableFile(atPath: url.path) else {
            throw ImporterError.unreadable(url.lastPathComponent)
        }
        let attributes = try? FileManager.default.attributesOfItem(atPath: url.path)
        guard let takenAt = attributes?[.creationDate] as? Date else {
            throw ImporterError.missingCreationDate(url.lastPathComponent)
        }
        return JournalEntry(id: UUID(), photoPath: url.path, caption: "", createdAt: takenAt)
    }
}
