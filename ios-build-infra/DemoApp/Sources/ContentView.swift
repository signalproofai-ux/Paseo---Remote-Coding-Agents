import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "hammer.fill")
                .font(.system(size: 56))
                .foregroundStyle(.teal)
            Text("Zero-cost iOS build pipeline")
                .font(.title2.bold())
            Text("Built with genuine macOS + Xcode CI")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding()
    }
}

#Preview {
    ContentView()
}
