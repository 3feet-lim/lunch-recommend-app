import Foundation
import Observation

@MainActor
final class RecommendationViewModel: ObservableObject {
    @Published var weather: Weather?
    @Published var mood: Mood?
    @Published var event: Event?
    @Published var priceRange: PriceRange?
    @Published var recommendations: [ScoredRestaurant] = []
    @Published var errorMessage: String?
    @Published var isLoading = false
    @Published var validationErrors: Set<CriteriaField> = []

    private var previousRecommendationIds: Set<String> = []

    private let locationService: LocationServiceProtocol
    private let apiClient: APIClientProtocol

    init(locationService: LocationServiceProtocol = LocationService(), apiClient: APIClientProtocol = APIClient()) {
        self.locationService = locationService
        self.apiClient = apiClient
    }

    func validateCriteria() -> Bool {
        var errors = Set<CriteriaField>()
        if weather == nil { errors.insert(.weather) }
        if mood == nil { errors.insert(.mood) }
        if event == nil { errors.insert(.event) }
        if priceRange == nil { errors.insert(.priceRange) }

        validationErrors = errors
        return errors.isEmpty
    }

    func requestRecommendation() async {
        guard validateCriteria(), let weather, let mood, let event, let priceRange else { return }
        errorMessage = nil
        isLoading = true
        defer { isLoading = false }

        do {
            let coordinate = try await locationService.getCurrentLocation()
            let criteria = RecommendationCriteria(weather: weather, mood: mood, event: event, priceRange: priceRange)
            let response = try await apiClient.requestRecommendation(coordinate: coordinate, criteria: criteria, excludeIds: previousRecommendationIds)
            recommendations = response.recommendations
            previousRecommendationIds.formUnion(response.recommendations.map(\.id))
        } catch {
            if let apiError = error as? APIError {
                switch apiError {
                case .serverUnavailable:
                    errorMessage = "Recommendation service is unavailable. Try again later."
                case .noResults:
                    errorMessage = "No matching restaurants were found."
                default:
                    errorMessage = "Failed to load recommendation."
                }
            } else if let locationError = error as? LocationError {
                switch locationError {
                case .permissionDenied:
                    errorMessage = "Location permission is denied."
                case .locationUnavailable:
                    errorMessage = "Current location is unavailable."
                default:
                    errorMessage = "Location error."
                }
            } else {
                errorMessage = "Unexpected error."
            }
        }
    }

    func requestNewRecommendation() async {
        guard !previousRecommendationIds.isEmpty else { return }
        await requestRecommendation()
    }

    func requestLocationPermission() async {
        do {
            _ = try await locationService.getCurrentLocation()
        } catch {
            if let locationError = error as? LocationError, locationError == .permissionDenied {
                errorMessage = "Location permission is denied."
            } else if let locationError = error as? LocationError, locationError == .permissionNotDetermined {
                errorMessage = "Location permission is not determined."
            } else {
                errorMessage = "Location permission request failed."
            }
        }
    }

    func clearError() {
        errorMessage = nil
    }
}
