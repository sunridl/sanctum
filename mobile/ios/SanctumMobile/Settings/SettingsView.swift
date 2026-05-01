import SwiftUI

struct SettingsView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss

    @State private var baseURL: String = BaseURLProvider.currentString
    @State private var showingDeleteConfirm = false
    @State private var deleteError: String?
    @State private var isDeleting = false

    var body: some View {
        Form {
            accountSection
            backendSection
            Section {
                Button("Log out", role: .destructive) {
                    auth.logout()
                    dismiss()
                }
                .accessibilityIdentifier("settings.logout")
            }
            dangerSection
        }
        .navigationTitle("Settings")
        .accessibilityIdentifier("settings.screen")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Done") { dismiss() }
                    .accessibilityIdentifier("settings.done")
            }
        }
        .confirmationDialog(
            "Delete account?",
            isPresented: $showingDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) { deleteAccount() }
                .accessibilityIdentifier("settings.deleteAccount.confirm")
            Button("Cancel", role: .cancel) { }
                .accessibilityIdentifier("settings.deleteAccount.cancel")
        } message: {
            Text("Your account, your clients, and all their notes will be removed. This cannot be undone.")
        }
    }

    // MARK: - Sections

    private var accountSection: some View {
        Section("Signed in as") {
            LabeledContent("Name", value: "\(auth.firstName) \(auth.lastName)".trimmingCharacters(in: .whitespaces))
                .accessibilityIdentifier("settings.profile.name")
            if let email = auth.email {
                LabeledContent("Email", value: email)
                    .accessibilityIdentifier("settings.profile.email")
            }
            if let role = auth.role {
                LabeledContent("Role", value: role.rawValue.capitalized)
                    .accessibilityIdentifier("settings.profile.role")
            }
        }
    }

    private var backendSection: some View {
        Section {
            TextField("Base URL", text: $baseURL)
                .keyboardType(.URL)
                .textContentType(.URL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("settings.baseURL")

            Button("Save") {
                BaseURLProvider.set(baseURL.trimmingCharacters(in: .whitespaces))
            }
            .accessibilityIdentifier("settings.baseURL.save")

            Button("Reset to default") {
                BaseURLProvider.reset()
                baseURL = BaseURLProvider.currentString
            }
            .accessibilityIdentifier("settings.baseURL.reset")
        } header: {
            Text("Backend")
        } footer: {
            // Heads-up: most users won't change this. Documenting the
            // override here so Appium engineers don't have to dig.
            Text("Default is \(BaseURLProvider.defaultURL). Tests can override at launch with -baseURL.")
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
                            .accessibilityIdentifier("settings.deleteAccount.loading")
                    }
                    Text("Delete account")
                }
            }
            .disabled(isDeleting)
            .accessibilityIdentifier("settings.deleteAccount")

            if let deleteError {
                Text(deleteError)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("settings.deleteAccount.error")
            }
        } header: {
            Text("Danger zone")
        }
    }

    // MARK: - Actions

    private func deleteAccount() {
        isDeleting = true
        deleteError = nil
        Task {
            defer { isDeleting = false }
            do {
                try await auth.deleteAccount()
                dismiss()
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
                dismiss()
            } catch {
                deleteError = "Could not delete account."
            }
        }
    }
}
