import Foundation

struct Coordinate: Equatable, Codable {
    let latitude: Double
    let longitude: Double
}

struct RecommendationRequest: Codable {
    let latitude: Double
    let longitude: Double
    let weather: Weather
    let mood: Mood
    let event: Event
    let priceRange: PriceRange
    let excludeIds: [String]

    enum CodingKeys: String, CodingKey {
        case latitude
        case longitude
        case weather
        case mood
        case event
        case priceRange = "price_range"
        case excludeIds = "exclude_ids"
    }
}

struct RecommendationCriteria: Equatable {
    let weather: Weather
    let mood: Mood
    let event: Event
    let priceRange: PriceRange
}

struct ScoredRestaurant: Identifiable, Codable, Equatable {
    let id: String
    let name: String
    let category: String
    let address: String
    let latitude: Double
    let longitude: Double
    let distance: Int
    let priceRange: PriceRange
    let naverMapUrl: String
    let score: Double

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case category
        case address
        case latitude
        case longitude
        case distance
        case score
        case priceRange = "price_range"
        case naverMapUrl = "naver_map_url"
    }
}

struct RecommendationResponse: Codable {
    let recommendations: [ScoredRestaurant]
    let totalSearched: Int
    let totalMatched: Int

    enum CodingKeys: String, CodingKey {
        case recommendations
        case totalSearched = "total_searched"
        case totalMatched = "total_matched"
    }
}
