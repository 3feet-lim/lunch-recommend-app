#if os(iOS)
import SwiftUI

@main
struct LunchMenuRecommenderApp: App {
    @StateObject private var recommendationVM = RecommendationViewModel()
    @StateObject private var settingsVM = SettingsViewModel()

    var body: some Scene {
        WindowGroup {
            TabView {
                OnboardingView(recommendationVM: recommendationVM, settingsVM: settingsVM)
                    .tabItem {
                        Label("Start", systemImage: "fork.knife")
                    }

                CriteriaInputView(viewModel: recommendationVM)
                    .tabItem {
                        Label("Recommend", systemImage: "list.bullet")
                    }

                SettingsView(viewModel: settingsVM)
                    .tabItem {
                        Label("Settings", systemImage: "gearshape")
                    }
            }
        }
    }
}
#endif
