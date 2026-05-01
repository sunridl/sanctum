import SwiftUI

struct ClientsListView: View {
    @Environment(AuthStore.self) private var auth

    @State private var clients: [Client] = []
    @State private var isLoading = false
    @State private var loadError: String?
    @State private var showingAdd = false
    @State private var showingSettings = false

    private var isTherapist: Bool { auth.role == .therapist }

    var body: some View {
        List {
            if let loadError {
                Section {
                    Text(loadError)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("clientsList.error")
                }
            }

            if clients.isEmpty && !isLoading && loadError == nil {
                // Distinct empty-state row so Appium can assert "no
                // clients yet" without inferring it from list length.
                Section {
                    Text(isTherapist
                         ? "No clients yet. Tap + to add one."
                         : "No shared clients yet.")
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("clientsList.empty")
                }
            }

            ForEach(clients) { client in
                NavigationLink(value: client) {
                    ClientRow(client: client)
                }
                .accessibilityIdentifier("clientsList.row.\(client.id)")
            }
            .onDelete(perform: isTherapist ? deleteClients : nil)
        }
        .navigationTitle("Clients")
        .accessibilityIdentifier("clientsList.screen")
        .navigationDestination(for: Client.self) { client in
            ClientDetailView(
                client: client,
                onDeleted: { id in
                    clients.removeAll { $0.id == id }
                },
                onUpdated: { updated in
                    if let idx = clients.firstIndex(where: { $0.id == updated.id }) {
                        clients[idx] = updated
                    }
                }
            )
        }
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    showingSettings = true
                } label: {
                    Image(systemName: "gearshape")
                }
                .accessibilityIdentifier("clientsList.settingsButton")
            }
            if isTherapist {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingAdd = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityIdentifier("clientsList.addButton")
                }
            }
        }
        .sheet(isPresented: $showingAdd) {
            NavigationStack {
                AddClientView { newClient in
                    clients.append(newClient)
                    showingAdd = false
                }
            }
        }
        .sheet(isPresented: $showingSettings) {
            NavigationStack {
                SettingsView()
            }
        }
        .refreshable { await load() }
        .overlay {
            if isLoading && clients.isEmpty {
                ProgressView()
                    .accessibilityIdentifier("clientsList.loading")
            }
        }
        .task { await load() }
    }

    private func load() async {
        guard let token = auth.token else { return }
        isLoading = true
        loadError = nil
        defer { isLoading = false }
        do {
            clients = try await ClientsService.list(token: token)
        } catch APIClient.APIError.http(let status, _) where status == 401 {
            // Stale/invalid token: drop the session and let the user log in again.
            auth.logout()
        } catch {
            loadError = "Could not load clients."
        }
    }

    private func deleteClients(at offsets: IndexSet) {
        guard let token = auth.token else { return }
        let targets = offsets.map { clients[$0] }
        // Optimistic update — remove locally first so the UI feels snappy,
        // restore on failure. With FastAPI on localhost the call rarely
        // fails, but when it does the user shouldn't be left thinking
        // they deleted something they didn't.
        clients.remove(atOffsets: offsets)
        Task { @MainActor in
            for client in targets {
                do {
                    try await ClientsService.delete(id: client.id, token: token)
                } catch {
                    if !clients.contains(client) { clients.append(client) }
                    loadError = "Could not delete \(client.fullName)."
                }
            }
        }
    }
}

private struct ClientRow: View {
    let client: Client

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(client.fullName)
                .font(.body)
            if let shared = client.shared_with {
                Text("Shared with \(shared.fullName)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("clientsList.row.\(client.id).sharedWith")
            }
        }
    }
}
