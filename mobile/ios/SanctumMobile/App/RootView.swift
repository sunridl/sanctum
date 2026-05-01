import SwiftUI

struct RootView: View {
    @State private var auth = AuthStore()

    var body: some View {
        NavigationStack {
            if auth.isLoggedIn {
                ClientsListView()
            } else {
                LoginView()
            }
        }
        .environment(auth)
    }
}
