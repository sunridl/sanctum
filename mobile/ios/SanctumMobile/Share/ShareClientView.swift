import SwiftUI

// Two-step share flow: lookup the psychiatrist by email first, show their
// name as a confirmation step, then commit the share. The lookup step
// catches typos and gives an Appium suite a clean state machine to
// assert against (locked → looked-up → confirmed).
struct ShareClientView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss

    let clientId: Int
    var onShared: (Psychiatrist) -> Void

    @State private var email = ""
    @State private var match: Psychiatrist?
    @State private var isLooking = false
    @State private var isSharing = false
    @State private var errorMessage: String?

    private var canLookup: Bool {
        !email.trimmingCharacters(in: .whitespaces).isEmpty && !isLooking && !isSharing
    }

    var body: some View {
        Form {
            Section("Psychiatrist email") {
                TextField("colleague@example.com", text: $email)
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("share.email")
                    .onChange(of: email) { _, _ in
                        // Any edit invalidates a previous lookup result —
                        // force the user to re-confirm the new email.
                        match = nil
                        errorMessage = nil
                    }

                Button {
                    lookup()
                } label: {
                    HStack {
                        if isLooking {
                            ProgressView()
                                .accessibilityIdentifier("share.lookup.loading")
                        }
                        Text("Look up")
                    }
                }
                .disabled(!canLookup)
                .accessibilityIdentifier("share.lookupButton")
            }

            if let match {
                Section("Confirm") {
                    LabeledContent("Name", value: match.fullName)
                        .accessibilityIdentifier("share.match.name")
                    LabeledContent("Email", value: match.email)
                        .accessibilityIdentifier("share.match.email")

                    Button {
                        share(with: match)
                    } label: {
                        HStack {
                            if isSharing {
                                ProgressView()
                                    .accessibilityIdentifier("share.confirm.loading")
                            }
                            Text("Share with this psychiatrist")
                        }
                    }
                    .disabled(isSharing)
                    .accessibilityIdentifier("share.confirmButton")
                }
            }

            if let errorMessage {
                Section {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("share.error")
                }
            }
        }
        .navigationTitle("Share client")
        .accessibilityIdentifier("share.screen")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Cancel") { dismiss() }
                    .accessibilityIdentifier("share.cancel")
            }
        }
    }

    private func lookup() {
        guard let token = auth.token else { return }
        isLooking = true
        errorMessage = nil
        match = nil
        Task {
            defer { isLooking = false }
            do {
                match = try await SharingService.lookup(email: email, token: token)
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
            } catch APIClient.APIError.http(let status, _) where status == 404 {
                errorMessage = "No psychiatrist found with that email."
            } catch {
                errorMessage = "Could not perform lookup."
            }
        }
    }

    private func share(with target: Psychiatrist) {
        guard let token = auth.token else { return }
        isSharing = true
        errorMessage = nil
        Task {
            defer { isSharing = false }
            do {
                try await SharingService.share(
                    clientId: clientId,
                    psychiatristEmail: target.email,
                    token: token
                )
                onShared(target)
                dismiss()
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
            } catch APIClient.APIError.http(let status, _) where status == 409 {
                errorMessage = "This client is already shared with someone."
            } catch APIClient.APIError.http(let status, _) where status == 404 {
                errorMessage = "Client or psychiatrist no longer exists."
            } catch {
                errorMessage = "Could not share client."
            }
        }
    }
}
