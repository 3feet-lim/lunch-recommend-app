// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "LunchMenuRecommender",
    platforms: [.iOS(.v17), .macOS(.v12)],
    products: [
        .library(name: "LunchMenuRecommender", targets: ["LunchMenuRecommender"]),
    ],
    targets: [
        .target(
            name: "LunchMenuRecommender",
            path: "Sources/LunchMenuRecommender"
        ),
        .testTarget(
            name: "LunchMenuRecommenderTests",
            dependencies: ["LunchMenuRecommender"],
            path: "Tests/LunchMenuRecommenderTests"
        ),
    ]
)
