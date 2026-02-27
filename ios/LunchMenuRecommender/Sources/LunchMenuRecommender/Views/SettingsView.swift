import SwiftUI

struct SettingsView: View {
    @ObservedObject var viewModel: SettingsViewModel

    var body: some View {
        Form {
            Toggle("Enable daily reminder", isOn: $viewModel.isNotificationEnabled)

            if viewModel.isNotificationEnabled {
                Stepper("Hour: \(viewModel.notificationHour)", value: $viewModel.notificationHour, in: 0...23)
                Stepper("Minute: \(viewModel.notificationMinute)", value: $viewModel.notificationMinute, in: 0...59)
            }

            Button("Apply") {
                Task {
                    await viewModel.saveNotificationSettings()
                }
            }
        }
        .navigationTitle("Settings")
    }
}
