#if os(iOS)
import SwiftUI

struct RecommendationResultView: View {
    @ObservedObject var viewModel: RecommendationViewModel

    var body: some View {
        NavigationView {
            VStack {
                if viewModel.recommendations.isEmpty {
                    Text("No result. Tap Recommendation again.")
                        .padding()
                } else {
                    List {
                        ForEach(viewModel.recommendations) { item in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(item.name).font(.headline)
                                Text(item.category)
                                Text("Distance: \(item.distance)m")
                                Text("Price: \(item.priceRange.displayName)")
                                Link("Open in Naver Map", destination: URL(string: item.naverMapUrl)!)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }

                Button("Try another 3") {
                    Task {
                        await viewModel.requestNewRecommendation()
                    }
                }
                .padding(.top, 8)
            }
            .navigationTitle("Recommendation")
        }
    }
}
#endif
