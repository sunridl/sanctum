import SwiftUI

struct SignupView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss

    @State private var email = ""
    @State private var password = ""
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var role: UserRole = .therapist
    @State private var isLoading = false
    @State private var errorMessage: String?

    // Mirrors the backend's password rule (Field(min_length=8)) — surfacing
    // it client-side avoids a round-trip for the most common signup mistake.
    private static let minPasswordLength = 8

    private var canSubmit: Bool {
        !email.trimmingCharacters(in: .whitespaces).isEmpty
            && password.count >= Self.minPasswordLength
            && !firstName.trimmingCharacters(in: .whitespaces).isEmpty
            && !lastName.trimmingCharacters(in: .whitespaces).isEmpty
            && !isLoading
    }

    var body: some View {
        Form {
            Section("Account") {
                TextField("Email", text: $email)
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("signup.email")

                SecureField("Password (8+ characters)", text: $password)
                    .textContentType(.newPassword)
                    .accessibilityIdentifier("signup.password")
            }

            Section("Name") {
                TextField("First name", text: $firstName)
                    .textContentType(.givenName)
                    .accessibilityIdentifier("signup.firstName")

                TextField("Last name", text: $lastName)
                    .textContentType(.familyName)
                    .accessibilityIdentifier("signup.lastName")
            }

            Section("Role") {
                Picker("Role", selection: $role) {
                    Text("Therapist").tag(UserRole.therapist)
                        .accessibilityIdentifier("signup.role.therapist")
                    Text("Psychiatrist").tag(UserRole.psychiatrist)
                        .accessibilityIdentifier("signup.role.psychiatrist")
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("signup.rolePicker")
            }

            Section {
                Button(action: submit) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .accessibilityIdentifier("signup.loading")
                        }
                        Text(isLoading ? "Creating account…" : "Create account")
                    }
                    .frame(maxWidth: .infinity)
                }
                .disabled(!canSubmit)
                .accessibilityIdentifier("signup.submit")
            }

            if let errorMessage {
                Section {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("signup.error")
                }
            }
        }
        .navigationTitle("Sign up")
        .accessibilityIdentifier("signup.screen")
    }

    private func submit() {
        isLoading = true
        errorMessage = nil
        let request = SignupRequest(
            email: email.trimmingCharacters(in: .whitespaces).lowercased(),
            password: password,
            first_name: firstName.trimmingCharacters(in: .whitespaces),
            last_name: lastName.trimmingCharacters(in: .whitespaces),
            role: role
        )
        Task {
            defer { isLoading = false }
            do {
                try await auth.signup(request)
                // SwiftUI doesn't pop pushed views when NavigationStack's
                // root content swaps (RootView reacts to isLoggedIn).
                // Dismiss explicitly so the RootView swap can show
                // ClientsListView instead of staying behind SignupView.
                dismiss()
            } catch APIClient.APIError.http(let status, _) where status == 409 {
                errorMessage = "An account with this email already exists."
            } catch APIClient.APIError.http(let status, _) where status == 422 {
                // Pydantic validation rejection — usually invalid email format
                // or password under 8 chars. Client-side checks should
                // catch most of these before submit.
                errorMessage = "Some fields are invalid. Check your email and password."
            } catch APIClient.APIError.transport {
                errorMessage = "Cannot reach server."
            } catch {
                errorMessage = "Could not create account."
            }
        }
    }
}
