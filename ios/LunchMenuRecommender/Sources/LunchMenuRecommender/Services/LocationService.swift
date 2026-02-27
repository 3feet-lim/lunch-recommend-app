import Foundation
import CoreLocation

protocol LocationServiceProtocol {
    func getCurrentLocation() async throws -> Coordinate
}

final class LocationService: NSObject, LocationServiceProtocol, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private var continuation: CheckedContinuation<Coordinate, Error>?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
    }

    func getCurrentLocation() async throws -> Coordinate {
        return try await withCheckedThrowingContinuation { continuation in
            switch manager.authorizationStatus {
            case .denied, .restricted:
                continuation.resume(throwing: LocationError.permissionDenied)
            case .notDetermined:
                self.continuation = continuation
                manager.requestWhenInUseAuthorization()
            case .authorizedAlways, .authorizedWhenInUse:
                self.continuation = continuation
                manager.requestLocation()
            @unknown default:
                continuation.resume(throwing: LocationError.permissionDenied)
            }
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        guard let continuation = continuation else { return }

        switch manager.authorizationStatus {
        case .denied, .restricted:
            continuation.resume(throwing: LocationError.permissionDenied)
            self.continuation = nil
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .notDetermined:
            continuation.resume(throwing: LocationError.permissionNotDetermined)
            self.continuation = nil
        @unknown default:
            continuation.resume(throwing: LocationError.locationUnavailable)
            self.continuation = nil
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let continuation = continuation else { return }
        guard let location = locations.last else {
            continuation.resume(throwing: LocationError.locationUnavailable)
            self.continuation = nil
            return
        }
        continuation.resume(returning: Coordinate(latitude: location.coordinate.latitude, longitude: location.coordinate.longitude))
        self.continuation = nil
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        guard let continuation = continuation else { return }
        continuation.resume(throwing: LocationError.locationUnavailable)
        self.continuation = nil
    }
}
