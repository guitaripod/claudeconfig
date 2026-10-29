import Foundation
import PhotoJournalCore

let storeURL = FileManager.default.temporaryDirectory.appendingPathComponent("photojournal-cli.json")
let store = JournalStore(fileURL: storeURL)
let sync = SyncClient(
    endpoint: URL(string: "https://sync.example.com/v1/entries")!,
    transport: { _, _ in 503 }
)
let lifecycle = AppLifecycle(store: store, sync: sync)
lifecycle.didFinishLaunching()

let importer = Importer(store: store)
_ = importer.importBatch(CommandLine.arguments.dropFirst().map { URL(fileURLWithPath: $0) })
lifecycle.willResignActive()
