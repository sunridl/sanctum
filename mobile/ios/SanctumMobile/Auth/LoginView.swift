import SwiftUI

struct LoginView: View {
    @Environment(AuthStore.self) private var auth

    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        Form {
            Section("Credentials") {
                TextField("Email", text: $email)
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("login.email")

                SecureField("Password", text: $password)
                    .textContentType(.password)
                    .accessibilityIdentifier("login.password")
            }

            Section {
                Button(action: submit) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .accessibilityIdentifier("login.loading")
                        }
                        Text(isLoading ? "Logging in…" : "Log in")
                    }
                    .frame(maxWidth: .infinity)
                }
                .disabled(email.isEmpty || password.isEmpty || isLoading)
                .accessibilityIdentifier("login.submit")
            }

            if let errorMessage {
                // Pin the error inside its own section with a stable
                // identifier so Appium can wait for it instead of polling.
                Section {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("login.error")
                }
            }

            Section {
                NavigationLink {
                    SignupView()
                } label: {
                    Text("Don't have an account? Sign up")
                }
                .accessibilityIdentifier("login.signupLink")
            }
        }
        .navigationTitle("Sanctum")
        .accessibilityIdentifier("login.screen")
    }

    private func submit() {
        isLoading = true
        errorMessage = nil
        Task {
            defer { isLoading = false }
            do {
                try await auth.login(email: email, password: password)
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                errorMessage = "Invalid credentials"
            } catch APIClient.APIError.transport {
                errorMessage = "Cannot reach server. Check the backend is running."
            } catch {
                errorMessage = "Unexpected error. Try again."
            }
        }
    }
}
