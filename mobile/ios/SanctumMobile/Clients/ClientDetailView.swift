import SwiftUI

struct ClientDetailView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss

    // The view owns a mutable copy so share/unshare can update the UI
    // without re-fetching. Parent gets notified via onUpdated.
    @State private var client: Client
    @State private var notes: [Note] = []
    @State private var isLoadingNotes = false
    @State private var notesError: String?

    @State private var showingAddNote = false
    @State private var showingShare = false
    @State private var showingDeleteConfirm = false
    @State private var isUnsharing = false
    @State private var isDeleting = false
    @State private var actionError: String?

    var onDeleted: (Int) -> Void
    var onUpdated: (Client) -> Void

    init(
        client: Client,
        onDeleted: @escaping (Int) -> Void = { _ in },
        onUpdated: @escaping (Client) -> Void = { _ in }
    ) {
        _client = State(initialValue: client)
        self.onDeleted = onDeleted
        self.onUpdated = onUpdated
    }

    private var isTherapist: Bool { auth.role == .therapist }

    var body: some View {
        Form {
            clientSection
            if isTherapist { sharingSection }
            notesSection
            if isTherapist { dangerSection }
        }
        .navigationTitle(client.fullName)
        .accessibilityIdentifier("clientDetail.screen")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showingAddNote = true
                } label: {
                    Image(systemName: "square.and.pencil")
                }
                .accessibilityIdentifier("clientDetail.addNoteButton")
            }
        }
        .sheet(isPresented: $showingAddNote) {
            NavigationStack {
                AddNoteView(clientId: client.id) { newNote in
                    notes.insert(newNote, at: 0)
                }
            }
        }
        .sheet(isPresented: $showingShare) {
            NavigationStack {
                ShareClientView(clientId: client.id) { shared in
                    let updated = client.with(sharedWith: shared)
                    client = updated
                    onUpdated(updated)
                }
            }
        }
        .confirmationDialog(
            "Delete \(client.fullName)?",
            isPresented: $showingDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) { deleteClient() }
                .accessibilityIdentifier("clientDetail.deleteConfirm")
            Button("Cancel", role: .cancel) { }
                .accessibilityIdentifier("clientDetail.deleteCancel")
        } message: {
            Text("This will remove the client and all of their notes. This cannot be undone.")
        }
        .task { await loadNotes() }
    }

    // MARK: - Sections

    private var clientSection: some View {
        Section("Client") {
            LabeledContent("Name", value: client.fullName)
                .accessibilityIdentifier("clientDetail.name")
        }
    }

    @ViewBuilder
    private var sharingSection: some View {
        Section("Sharing") {
            if let shared = client.shared_with {
                LabeledContent("Shared with", value: shared.fullName)
                    .accessibilityIdentifier("clientDetail.sharedWith")
                LabeledContent("Email", value: shared.email)
                    .accessibilityIdentifier("clientDetail.sharedWith.email")
                Button {
                    unshare()
                } label: {
                    HStack {
                        if isUnsharing {
                            ProgressView()
                                .accessibilityIdentifier("clientDetail.unshare.loading")
                        }
                        Text("Stop sharing")
                    }
                }
                .disabled(isUnsharing)
                .accessibilityIdentifier("clientDetail.unshareButton")
            } else {
                Text("Not shared")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("clientDetail.sharedWith.none")
                Button("Share with a psychiatrist") {
                    showingShare = true
                }
                .accessibilityIdentifier("clientDetail.shareButton")
            }
        }
    }

    @ViewBuilder
    private var notesSection: some View {
        Section("Notes") {
            if isLoadingNotes && notes.isEmpty {
                ProgressView()
                    .accessibilityIdentifier("clientDetail.notes.loading")
            } else if let notesError {
                Text(notesError)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("clientDetail.notes.error")
            } else if notes.isEmpty {
                Text("No notes yet.")
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("clientDetail.notes.empty")
            } else {
                ForEach(notes) { note in
                    NoteRow(note: note)
                        .accessibilityIdentifier("clientDetail.note.\(note.id)")
                }
            }
        }
    }

    @ViewBuilder
    private var dangerSection: some View {
        Section {
            Button(role: .destructive) {
                showingDeleteConfirm = true
            } label: {
                HStack {
                    if isDeleting {
                        ProgressView()
                            .accessibilityIdentifier("clientDetail.delete.loading")
                    }
                    Text("Delete client")
                }
            }
            .disabled(isDeleting)
            .accessibilityIdentifier("clientDetail.deleteButton")

            if let actionError {
                Text(actionError)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("clientDetail.delete.error")
            }
        }
    }

    // MARK: - Actions

    private func loadNotes() async {
        guard let token = auth.token else { return }
        isLoadingNotes = true
        notesError = nil
        defer { isLoadingNotes = false }
        do {
            notes = try await NotesService.list(clientId: client.id, token: token)
        } catch APIClient.APIError.http(let status, _) where status == 401 {
            auth.logout()
        } catch {
            notesError = "Could not load notes."
        }
    }

    private func unshare() {
        guard let token = auth.token else { return }
        isUnsharing = true
        actionError = nil
        Task {
            defer { isUnsharing = false }
            do {
                try await SharingService.unshare(clientId: client.id, token: token)
                let updated = client.with(sharedWith: nil)
                client = updated
                onUpdated(updated)
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
            } catch {
                actionError = "Could not stop sharing."
            }
        }
    }

    private func deleteClient() {
        guard let token = auth.token else { return }
        isDeleting = true
        actionError = nil
        Task {
            defer { isDeleting = false }
            do {
                try await ClientsService.delete(id: client.id, token: token)
                onDeleted(client.id)
                dismiss()
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
            } catch {
                actionError = "Could not delete client."
            }
        }
    }
}

// Inline row so the file is self-contained — small enough that pulling
// it into its own file would be overkill.
private struct NoteRow: View {
    let note: Note

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(note.content)
                .font(.body)
            HStack(spacing: 8) {
                Text(note.authorDisplayName)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if note.is_private {
                    Label("Private", systemImage: "lock")
                        .font(.caption)
                        .foregroundStyle(.orange)
                        .accessibilityIdentifier("note.\(note.id).privateBadge")
                }
            }
        }
        .padding(.vertical, 2)
    }
}
