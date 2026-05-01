import SwiftUI

struct AddClientView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss

    var onCreated: (Client) -> Void

    @State private var firstName = ""
    @State private var lastName = ""
    @State private var isSaving = false
    @State private var errorMessage: String?

    private var canSubmit: Bool {
        !firstName.trimmingCharacters(in: .whitespaces).isEmpty
            && !lastName.trimmingCharacters(in: .whitespaces).isEmpty
            && !isSaving
    }

    var body: some View {
        Form {
            Section("Name") {
                TextField("First name", text: $firstName)
                    .textContentType(.givenName)
                    .accessibilityIdentifier("addClient.firstName")
                TextField("Last name", text: $lastName)
                    .textContentType(.familyName)
                    .accessibilityIdentifier("addClient.lastName")
            }

            if let errorMessage {
                Section {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("addClient.error")
                }
            }
        }
        .navigationTitle("New client")
        .accessibilityIdentifier("addClient.screen")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Cancel") { dismiss() }
                    .accessibilityIdentifier("addClient.cancel")
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Save") { save() }
                    .disabled(!canSubmit)
                    .accessibilityIdentifier("addClient.save")
            }
        }
    }

    private func save() {
        guard let token = auth.token else { return }
        isSaving = true
        errorMessage = nil
        Task {
            defer { isSaving = false }
            do {
                let client = try await ClientsService.create(
                    ClientCreate(
                        first_name: firstName.trimmingCharacters(in: .whitespaces),
                        last_name: lastName.trimmingCharacters(in: .whitespaces)
                    ),
                    token: token
                )
                onCreated(client)
                dismiss()
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
            } catch APIClient.APIError.http(let status, _) where status == 404 {
                // Backend returns 404 for non-therapist callers (anti-enum).
                // In practice the UI never shows the add button for
                // psychiatrists, so this branch is defensive only.
                errorMessage = "Only therapists can add clients."
            } catch {
                errorMessage = "Could not save client."
            }
        }
    }
}
