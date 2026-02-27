import XCTest
@testable import LunchMenuRecommender

final class UnitTests: XCTestCase {
    func testCriteriaValidation() async {
        let vm = RecommendationViewModel()
        vm.weather = .sunny
        vm.mood = .happy
        vm.event = .none
        vm.priceRange = .medium
        XCTAssertTrue(vm.validateCriteria())
        XCTAssertTrue(vm.validationErrors.isEmpty)
    }

    func testNotificationServiceDefaults() {
        let service = NotificationService()
        XCTAssertNotNil(service)
    }
}
