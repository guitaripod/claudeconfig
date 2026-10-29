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
        print("AppLifecycle: launched \(Self.version) with \(store.allEntries.count) entries")
        do {
            try sync.push(store.allEntries)
        } catch {
            print("AppLifecycle: launch sync failed: \(error)")
        }
    }

    public func willResignActive() {
        do {
            try store.save()
        } catch {
            print("AppLifecycle: background save failed: \(error)")
        }
    }
}
