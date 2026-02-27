import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var notificationHour: Int = 11
    @Published var notificationMinute: Int = 30
    @Published var isNotificationEnabled: Bool = false

    private let notificationService: NotificationServiceProtocol

    init(notificationService: NotificationServiceProtocol = NotificationService()) {
        self.notificationService = notificationService
    }

    func saveNotificationSettings() async {
        guard isNotificationEnabled else {
            disableNotification()
            return
        }
        do {
            try await notificationService.scheduleDailyNotification(at: notificationHour, minute: notificationMinute)
        } catch {
            isNotificationEnabled = false
        }
    }

    func disableNotification() {
        notificationService.cancelAllNotifications()
        isNotificationEnabled = false
    }
}
