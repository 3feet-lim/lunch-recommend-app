import Foundation
import UserNotifications

protocol NotificationServiceProtocol {
    func scheduleDailyNotification(at hour: Int, minute: Int) async throws
    func cancelAllNotifications()
    func requestPermission() async throws -> Bool
}

final class NotificationService: NotificationServiceProtocol {
    private let center = UNUserNotificationCenter.current()
    private let identifier = "lunch-menu-daily-reminder"

    func requestPermission() async throws -> Bool {
        do {
            let status = try await center.requestAuthorization(options: [.alert, .sound, .badge])
            return status
        }
    }

    func scheduleDailyNotification(at hour: Int, minute: Int) async throws {
        guard hour >= 0 && hour < 24 && minute >= 0 && minute < 60 else {
            throw NotificationError.schedulingFailed
        }

        let authorized = try await requestPermission()
        guard authorized else { throw NotificationError.permissionDenied }

        let content = UNMutableNotificationContent()
        content.title = "Lunch recommendation"
        content.body = "It's lunchtime! Open the app for lunch recommendation."
        content.sound = .default

        var date = DateComponents()
        date.hour = hour
        date.minute = minute

        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)
        do {
            try await center.add(request)
        } catch {
            throw NotificationError.schedulingFailed
        }
    }

    func cancelAllNotifications() {
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
        center.removeAllDeliveredNotifications()
    }
}
