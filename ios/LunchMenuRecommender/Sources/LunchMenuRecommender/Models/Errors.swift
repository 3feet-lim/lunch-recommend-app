import Foundation

enum LocationError: Error, Equatable {
    case permissionDenied
    case permissionNotDetermined
    case locationUnavailable
}

enum APIError: Error, Equatable {
    case serverUnavailable
    case invalidResponse
    case networkFailure
    case noResults
}

enum NotificationError: Error, Equatable {
    case permissionDenied
    case schedulingFailed
}
