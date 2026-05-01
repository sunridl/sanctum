import SwiftUI

struct AddNoteView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss

    let clientId: Int
    var onCreated: (Note) -> Void

    @State private var content = ""
    @State private var isPrivate = true
    @State private var isSaving = false
    @State private var errorMessage: String?

    private var isTherapist: Bool { auth.role == .therapist }

    private var canSubmit: Bool {
        !content.trimmingCharacters(in: .whitespaces).isEmpty && !isSaving
    }

    var body: some View {
        Form {
            Section("Note") {
                TextField("Write a note…", text: $content, axis: .vertical)
                    .lineLimit(4...10)
                    .accessibilityIdentifier("addNote.content")
            }

            // Privacy is a therapist-only concept on the backend — a
            // psychiatrist's note can never be private (the API would 404
            // even if we sent is_private=true). Hiding the toggle for
            // psychiatrists keeps the UI honest.
            if isTherapist {
                Section("Visibility") {
                    Toggle("Private (only visible to therapist)", isOn: $isPrivate)
                        .accessibilityIdentifier("addNote.privateToggle")
                }
            }

            if let errorMessage {
                Section {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("addNote.error")
                }
            }
        }
        .navigationTitle("New note")
        .accessibilityIdentifier("addNote.screen")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Cancel") { dismiss() }
                    .accessibilityIdentifier("addNote.cancel")
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Save") { save() }
                    .disabled(!canSubmit)
                    .accessibilityIdentifier("addNote.save")
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
                let note = try await NotesService.create(
                    clientId: clientId,
                    data: NoteCreate(
                        content: content.trimmingCharacters(in: .whitespaces),
                        // Force public for psychiatrists in case the toggle
                        // ever leaks into their UI by mistake.
                        is_private: isTherapist ? isPrivate : false
                    ),
                    token: token
                )
                onCreated(note)
                dismiss()
            } catch APIClient.APIError.http(let status, _) where status == 401 {
                auth.logout()
            } catch APIClient.APIError.http(let status, _) where status == 404 {
                errorMessage = "This client is no longer accessible."
            } catch {
                errorMessage = "Could not save note."
            }
        }
    }
}
