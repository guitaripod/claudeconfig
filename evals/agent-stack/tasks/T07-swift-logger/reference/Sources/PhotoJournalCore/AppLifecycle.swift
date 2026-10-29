import Foundation

public final class AppLifecycle {
    public static let version = "1.4.0"

    private let store: JournalStore
    private let sync: SyncClient

    public init(store: JournalStore, sync: SyncClient) {
        self.store = store
        self.sync = sync
    }

    public func didFinishLaunching() {
        AppLogger.shared.info(
            "launched \(Self.version) with \(store.allEntries.count) entries",
            category: .lifecycle
        )
        do {
            try sync.push(store.allEntries)
        } catch {
            AppLogger.shared.error("launch sync failed: \(error)", category: .lifecycle)
        }
    }

    public func willResignActive() {
        do {
            try store.save()
        } catch {
            AppLogger.shared.error("background save failed: \(error)", category: .lifecycle)
        }
    }
}
