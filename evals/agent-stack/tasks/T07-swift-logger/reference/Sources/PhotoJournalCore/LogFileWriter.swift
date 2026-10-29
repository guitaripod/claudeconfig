import Foundation

public final class LogFileWriter: @unchecked Sendable {
    public static let defaultMaxBytes = 1_048_576
    public static let currentFileName = "photojournal.log"
    public static let previousFileName = "photojournal.previous.log"

    public let currentFileURL: URL
    private let previousFileURL: URL
    private let maxBytes: Int
    private let queue = DispatchQueue(label: "com.example.photojournal.logfile", qos: .utility)

    public init(directory: URL, maxBytes: Int = LogFileWriter.defaultMaxBytes) {
        self.currentFileURL = directory.appendingPathComponent(Self.currentFileName)
        self.previousFileURL = directory.appendingPathComponent(Self.previousFileName)
        self.maxBytes = maxBytes
    }

    public func append(_ line: String) {
        let data = Data((line + "\n").utf8)
        queue.async { [self] in
            try? appendData(data)
        }
    }

    private func appendData(_ data: Data) throws {
        let fileManager = FileManager.default
        try fileManager.createDirectory(
            at: currentFileURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try rotateIfNeeded(adding: data.count)
        if !fileManager.fileExists(atPath: currentFileURL.path) {
            fileManager.createFile(atPath: currentFileURL.path, contents: nil)
        }
        let handle = try FileHandle(forWritingTo: currentFileURL)
        defer { try? handle.close() }
        _ = try handle.seekToEnd()
        try handle.write(contentsOf: data)
    }

    private func rotateIfNeeded(adding incoming: Int) throws {
        guard currentSize + incoming > maxBytes else {
            return
        }
        let fileManager = FileManager.default
        if fileManager.fileExists(atPath: previousFileURL.path) {
            try fileManager.removeItem(at: previousFileURL)
        }
        if fileManager.fileExists(atPath: currentFileURL.path) {
            try fileManager.moveItem(at: currentFileURL, to: previousFileURL)
        }
    }

    private var currentSize: Int {
        let attributes = try? FileManager.default.attributesOfItem(atPath: currentFileURL.path)
        return (attributes?[.size] as? NSNumber)?.intValue ?? 0
    }
}
