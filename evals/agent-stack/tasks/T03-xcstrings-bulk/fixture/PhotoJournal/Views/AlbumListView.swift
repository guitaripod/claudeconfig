import SwiftUI

struct AlbumListView: View {
    let albums: [Album]
    let onDelete: (Album) -> Void
    let onCreate: () -> Void
    @State private var pendingDelete: Album?

    var body: some View {
        List {
            ForEach(albums) { album in
                Text(album.title)
                    .swipeActions {
                        Button(role: .destructive) {
                            pendingDelete = album
                        } label: {
                            Image(systemName: "trash")
                        }
                    }
            }
        }
        .navigationTitle(String(localized: "tab.albums"))
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button(String(localized: "album.new"), action: onCreate)
            }
        }
        .confirmationDialog(
            String(format: String(localized: "album.delete.confirm"), pendingDelete?.title ?? ""),
            isPresented: Binding(
                get: { pendingDelete != nil },
                set: { if !$0 { pendingDelete = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button(String(localized: "common.delete"), role: .destructive) {
                if let album = pendingDelete {
                    onDelete(album)
                }
                pendingDelete = nil
            }
            Button(String(localized: "common.cancel"), role: .cancel) {
                pendingDelete = nil
            }
        }
    }
}
