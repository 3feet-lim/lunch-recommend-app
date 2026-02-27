import SwiftUI

struct CriteriaInputView: View {
    @ObservedObject var viewModel: RecommendationViewModel

    var body: some View {
        NavigationView {
            Form {
                Section("Weather") {
                    Picker("Weather", selection: Binding(
                        get: { viewModel.weather ?? .sunny },
                        set: { viewModel.weather = $0 }
                    )) {
                        ForEach(Weather.allCases, id: \.self) { item in
                            Text(item.displayName).tag(item)
                        }
                    }
                }

                Section("Mood") {
                    Picker("Mood", selection: Binding(
                        get: { viewModel.mood ?? .normal },
                        set: { viewModel.mood = $0 }
                    )) {
                        ForEach(Mood.allCases, id: \.self) { item in
                            Text(item.displayName).tag(item)
                        }
                    }
                }

                Section("Event") {
                    Picker("Event", selection: Binding(
                        get: { viewModel.event ?? .none },
                        set: { viewModel.event = $0 }
                    )) {
                        ForEach(Event.allCases, id: \.self) { item in
                            Text(item.displayName).tag(item)
                        }
                    }
                }

                Section("Price") {
                    Picker("Price", selection: Binding(
                        get: { viewModel.priceRange ?? .medium },
                        set: { viewModel.priceRange = $0 }
                    )) {
                        ForEach(PriceRange.allCases, id: \.self) { item in
                            Text(item.displayName).tag(item)
                        }
                    }
                }

                Button("Get Recommendation") {
                    Task {
                        await viewModel.requestRecommendation()
                    }
                }

                if let error = viewModel.errorMessage {
                    Text(error).foregroundColor(.red)
                }

                if !viewModel.recommendations.isEmpty {
                    NavigationLink("See Results") {
                        RecommendationResultView(viewModel: viewModel)
                    }
                }
            }
            .navigationTitle("Lunch Criteria")
        }
    }
}
