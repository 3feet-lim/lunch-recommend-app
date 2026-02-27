import SwiftUI

struct OnboardingView: View {
    @ObservedObject var recommendationVM: RecommendationViewModel
    @ObservedObject var settingsVM: SettingsViewModel

    var body: some View {
        NavigationView {
            Form {
                Section("Location Permission") {
                    Button("Enable location permission") {
                        Task {
                            await recommendationVM.requestLocationPermission()
                        }
                    }
                }

                Section("Daily reminder") {
                    Toggle("Enable daily reminder", isOn: $settingsVM.isNotificationEnabled)
                    if settingsVM.isNotificationEnabled {
                        DatePicker(
                            "Reminder time",
                            selection: Binding(
                                get: {
                                    Calendar.current.date(from: DateComponents(hour: settingsVM.notificationHour, minute: settingsVM.notificationMinute)) ?? Date()
                                },
                                set: { newValue in
                                    let comps = Calendar.current.dateComponents([.hour, .minute], from: newValue)
                                    settingsVM.notificationHour = comps.hour ?? 11
                                    settingsVM.notificationMinute = comps.minute ?? 30
                                }
                            ),
                            displayedComponents: .hourAndMinute
                        )
                        Button("Save") {
                            Task {
                                await settingsVM.saveNotificationSettings()
                            }
                        }
                    }
                }
            }
            .navigationTitle("Welcome")
        }
    }
}
