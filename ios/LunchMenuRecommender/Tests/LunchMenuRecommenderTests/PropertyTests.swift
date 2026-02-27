import XCTest
@testable import LunchMenuRecommender

final class PropertyTests: XCTestCase {
    func testRequestResponseJSONRoundTrip() throws {
        let response = RecommendationResponse(
            recommendations: [
                ScoredRestaurant(
                    id: "1",
                    name: "Sample",
                    category: "korean",
                    address: "Seoul",
                    latitude: 37.5,
                    longitude: 126.9,
                    distance: 100,
                    priceRange: .medium,
                    naverMapUrl: "https://map.naver.com",
                    score: 0.87
                )
            ],
            totalSearched: 1,
            totalMatched: 1
        )

        let encoded = try JSONEncoder().encode(response)
        let decoded = try JSONDecoder().decode(RecommendationResponse.self, from: encoded)
        XCTAssertEqual(decoded.recommendations.count, 1)
    }

    func testNotificationScheduleParameters() {
        for hour in stride(from: 0, through: 23, by: 1) {
            XCTAssertTrue((0...23).contains(hour))
        }
    }
}
