import Foundation

protocol APIClientProtocol {
    func requestRecommendation(
        coordinate: Coordinate,
        criteria: RecommendationCriteria,
        excludeIds: Set<String>
    ) async throws -> RecommendationResponse

    func healthCheck() async throws -> Bool
}

final class APIClient: APIClientProtocol {
    private let baseURL: URL
    private let session: URLSession

    init(baseURL: URL = URL(string: "http://localhost:8000")!, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func requestRecommendation(
        coordinate: Coordinate,
        criteria: RecommendationCriteria,
        excludeIds: Set<String>
    ) async throws -> RecommendationResponse {
        let requestModel = RecommendationRequest(
            latitude: coordinate.latitude,
            longitude: coordinate.longitude,
            weather: criteria.weather,
            mood: criteria.mood,
            event: criteria.event,
            priceRange: criteria.priceRange,
            excludeIds: Array(excludeIds)
        )

        guard let url = URL(string: "/api/v1/recommend", relativeTo: baseURL) else {
            throw APIError.networkFailure
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 10
        request.httpBody = try JSONEncoder().encode(requestModel)

        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }

            if httpResponse.statusCode == 200 {
                do {
                    return try JSONDecoder().decode(RecommendationResponse.self, from: data)
                } catch {
                    throw APIError.invalidResponse
                }
            }

            switch httpResponse.statusCode {
            case 204:
                return RecommendationResponse(recommendations: [], totalSearched: 0, totalMatched: 0)
            case 422, 500, 502, 504:
                throw APIError.serverUnavailable
            default:
                throw APIError.networkFailure
            }
        } catch {
            throw APIError.networkFailure
        }
    }

    func healthCheck() async throws -> Bool {
        guard let url = URL(string: "/api/v1/health", relativeTo: baseURL) else {
            throw APIError.networkFailure
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 10

        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }
            return httpResponse.statusCode == 200 && (try? JSONDecoder().decode([String: String].self, from: data)) != nil
        } catch {
            throw APIError.serverUnavailable
        }
    }
}
