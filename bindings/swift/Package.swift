// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "STRling",
    platforms: [
        .macOS(.v10_15),
        .iOS(.v13),
        .tvOS(.v13),
        .watchOS(.v6)
    ],
    products: [
        // Products define the executables and libraries a package produces, making them visible to other packages.
        .library(
            name: "STRling",
            targets: ["STRling"]),
    ],
    targets: [
        // Targets are the basic building blocks of a package, defining a module or a test suite.
        // Targets can depend on other targets in this package and products from dependencies.
        .target(
            name: "STRling",
            dependencies: [],
            path: "Sources/STRling"),
        .testTarget(
            name: "STRlingUnitTests",
            dependencies: ["STRling"],
            path: "Tests/STRlingUnitTests"),
        .testTarget(
            name: "STRlingE2ETests",
            dependencies: ["STRling"],
            path: "Tests/STRlingE2ETests"),
        .testTarget(
            name: "STRlingConformanceTests",
            dependencies: ["STRling"],
            path: "Tests/STRlingConformanceTests",
            resources: [
                .process("Resources")
            ]),
    ]
)
