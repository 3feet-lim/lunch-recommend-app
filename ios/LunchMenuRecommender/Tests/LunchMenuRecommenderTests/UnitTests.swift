import XCTest
@testable import LunchMenuRecommender

@MainActor
final class UnitTests: XCTestCase {
    func testCriteriaValidation() async {
        let vm = RecommendationViewModel()

        var valid = false
        var errorsEmpty = false

        await MainActor.run {
            vm.weather = .sunny
            vm.mood = .happy
            vm.event = Event.none
            vm.priceRange = .medium
            valid = vm.validateCriteria()
            errorsEmpty = vm.validationErrors.isEmpty
        }

        XCTAssertTrue(valid)
        XCTAssertTrue(errorsEmpty)
    }

    #if os(iOS)
    func testNotificationServiceDefaults() {
        let service = NotificationService()
        XCTAssertNotNil(service)
    }
    #else
    func testNotificationServiceDefaults() throws {
        throw XCTSkip("NotificationService is unavailable in this test environment.")
    }
    #endif
}
