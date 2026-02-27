import Foundation

enum Weather: String, CaseIterable, Codable {
    case sunny
    case cloudy
    case rainy
    case snowy

    var displayName: String {
        switch self {
        case .sunny: return "Sunny"
        case .cloudy: return "Cloudy"
        case .rainy: return "Rainy"
        case .snowy: return "Snowy"
        }
    }
}

enum Mood: String, CaseIterable, Codable {
    case happy
    case normal
    case sad
    case tired

    var displayName: String {
        switch self {
        case .happy: return "Happy"
        case .normal: return "Normal"
        case .sad: return "Sad"
        case .tired: return "Tired"
        }
    }
}

enum Event: String, CaseIterable, Codable {
    case teamDinner = "team_dinner"
    case date
    case solo
    case diet
    case none

    var displayName: String {
        switch self {
        case .teamDinner: return "Team Dinner"
        case .date: return "Date"
        case .solo: return "Solo"
        case .diet: return "Diet"
        case .none: return "None"
        }
    }
}

enum PriceRange: String, CaseIterable, Codable {
    case low
    case medium
    case high

    var displayName: String {
        switch self {
        case .low: return "Low"
        case .medium: return "Medium"
        case .high: return "High"
        }
    }
}

enum CriteriaField: String, CaseIterable {
    case weather
    case mood
    case event
    case priceRange
}
