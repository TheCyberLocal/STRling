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
        .library(
            name: "STRling",
            targets: ["STRling"]),
    ],
    targets: [
        .target(
            name: "CSTRlingNative",
            path: "Sources/CSTRlingNative",
            publicHeadersPath: "include",
            linkerSettings: [
                .linkedLibrary("dl", .when(platforms: [.linux]))
            ]),
        .target(
            name: "STRling",
            dependencies: ["CSTRlingNative"],
            path: "Sources/STRling"),
        .testTarget(
            name: "STRlingAdapterTests",
            dependencies: ["STRling"],
            path: "Tests/STRlingAdapterTests"),
    ]
)
