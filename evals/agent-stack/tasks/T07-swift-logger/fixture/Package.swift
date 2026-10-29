// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PhotoJournal",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "PhotoJournalCore", targets: ["PhotoJournalCore"]),
        .executable(name: "photojournal-cli", targets: ["photojournal-cli"]),
    ],
    targets: [
        .target(name: "PhotoJournalCore"),
        .executableTarget(name: "photojournal-cli", dependencies: ["PhotoJournalCore"]),
    ]
)
