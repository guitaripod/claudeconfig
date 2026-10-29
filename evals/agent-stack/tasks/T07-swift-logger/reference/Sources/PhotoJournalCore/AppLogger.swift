import Foundation
#if canImport(OSLog)
import OSLog
#endif

public enum LogCategory: String, CaseIterable, Sendable {
    case lifecycle
    case importing
    case persistence
    case sync
}

public enum LogLevel: String, Sendable {
    case debug
    case info
    case error
}

public final class AppLogger: @unchecked Sendable {
    public static let shared = AppLogger(
        subsystem: "com.example.photojournal",
        writer: LogFileWriter(directory: defaultLogsDirectory())
    )

    public var logFileURL: URL {
        writer.currentFileURL
    }

    private let writer: LogFileWriter
    #if canImport(OSLog)
    private let osLoggers: [LogCategory: Logger]
    #endif

    public init(subsystem: String, writer: LogFileWriter) {
        self.writer = writer
        #if canImport(OSLog)
        self.osLoggers = Dictionary(uniqueKeysWithValues: LogCategory.allCases.map {
            ($0, Logger(subsystem: subsystem, category: $0.rawValue))
        })
        #endif
    }

    public func debug(_ message: String, category: LogCategory) {
        record(.debug, message, category: category)
    }

    public func info(_ message: String, category: LogCategory) {
        record(.info, message, category: category)
    }

    public func error(_ message: String, category: LogCategory) {
        record(.error, message, category: category)
    }

    private func record(_ level: LogLevel, _ message: String, category: LogCategory) {
        #if canImport(OSLog)
        forwardToOSLog(level, message, category: category)
        #endif
        writer.append(formatLine(level, message, category: category))
    }

    #if canImport(OSLog)
    private func forwardToOSLog(_ level: LogLevel, _ message: String, category: LogCategory) {
        guard let osLogger = osLoggers[category] else {
            return
        }
        switch level {
        case .debug:
            osLogger.debug("\(message, privacy: .public)")
        case .info:
            osLogger.info("\(message, privacy: .public)")
        case .error:
            osLogger.error("\(message, privacy: .public)")
        }
    }
    #endif

    private func formatLine(_ level: LogLevel, _ message: String, category: LogCategory) -> String {
        let timestamp = ISO8601DateFormatter().string(from: Date())
        return "\(timestamp) [\(level.rawValue)] [\(category.rawValue)] \(message)"
    }

    private static func defaultLogsDirectory() -> URL {
        URL(fileURLWithPath: NSHomeDirectory(), isDirectory: true)
            .appendingPathComponent("Library/Logs/PhotoJournal", isDirectory: true)
    }
}
