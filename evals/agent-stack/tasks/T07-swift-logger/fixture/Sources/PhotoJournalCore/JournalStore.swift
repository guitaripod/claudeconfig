import Foundation

public struct JournalEntry: Codable, Equatable, Sendable {
    public let id: UUID
    public let photoPath: String
    public let caption: String
    public let createdAt: Date

    public init(id: UUID, photoPath: String, caption: String, createdAt: Date) {
        self.id = id
        self.photoPath = photoPath
        self.caption = caption
        self.createdAt = createdAt
    }
}

public enum JournalStoreError: Error, Equatable {
    case writeFailed(String)
    case notFound(UUID)
}

public final class JournalStore {
    private let fileURL: URL
    private var entries: [JournalEntry]

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.entries = JournalStore.load(from: fileURL)
    }

    public var allEntries: [JournalEntry] {
        entries
    }

    public func add(_ entry: JournalEntry) {
        entries.append(entry)
        do {
            try save()
        } catch {
            print("JournalStore: save failed after adding \(entry.id): \(error)")
        }
    }

    public func remove(id: UUID) throws {
        guard let index = entries.firstIndex(where: { $0.id == id }) else {
            throw JournalStoreError.notFound(id)
        }
        entries.remove(at: index)
        try save()
    }

    public func save() throws {
        let data = try JSONEncoder().encode(entries)
        do {
            try data.write(to: fileURL, options: .atomic)
        } catch {
            print("JournalStore: write to \(fileURL.lastPathComponent) failed: \(error)")
            throw JournalStoreError.writeFailed(error.localizedDescription)
        }
    }

    private static func load(from url: URL) -> [JournalEntry] {
        guard FileManager.default.fileExists(atPath: url.path) else {
            return []
        }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode([JournalEntry].self, from: data)
        } catch {
            print("JournalStore: could not decode \(url.lastPathComponent), starting empty: \(error)")
            return []
        }
    }
}
