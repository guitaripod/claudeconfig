import SwiftUI

struct HomeView: View {
    let userName: String
    let usedBytes: String
    let totalBytes: String
    let isLowPowerModeEnabled: Bool
    let exportedCount: Int?
    let entryCount: Int
    let onDone: () -> Void

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text(String(format: String(localized: "welcome.back"), userName))
                    .font(.title2.bold())

                Text(String(format: String(localized: "storage.used"), usedBytes, totalBytes))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                Text(String.localizedStringWithFormat(String(localized: "journal.entries.count"), entryCount))
                    .font(.footnote)

                if let exportedCount {
                    Text(String.localizedStringWithFormat(String(localized: "export.success"), exportedCount))
                        .font(.footnote)
                }

                if isLowPowerModeEnabled {
                    Label(String(localized: "sync.paused.lowpower"), systemImage: "bolt.slash")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }

                Spacer()
            }
            .padding()
            .navigationTitle(String(localized: "tab.journal"))
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(String(localized: "common.done"), action: onDone)
                }
            }
        }
    }
}
