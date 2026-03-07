#if os(iOS)
import SwiftUI

struct SettingsView: View {
    @ObservedObject var viewModel: SettingsViewModel

    var body: some View {
        Form {
            Toggle("Enable daily reminder", isOn: Binding(
                get: { viewModel.isNotificationEnabled },
                set: { viewModel.isNotificationEnabled = $0 }
            ))

            if viewModel.isNotificationEnabled {
                Stepper(
                    "Hour: \(viewModel.notificationHour)",
                    value: Binding(
                        get: { viewModel.notificationHour },
                        set: { viewModel.notificationHour = $0 }
                    ),
                    in: 0...23
                )
                Stepper(
                    "Minute: \(viewModel.notificationMinute)",
                    value: Binding(
                        get: { viewModel.notificationMinute },
                        set: { viewModel.notificationMinute = $0 }
                    ),
                    in: 0...59
                )
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
#endif
