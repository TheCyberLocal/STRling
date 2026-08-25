// Generated from the canonical standard-library registry. Do not edit.
// These lexical helpers record Simply recipes; they do not validate semantics.
import Foundation

public enum Essential {
    public static let sourceSHA256 = "94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d"
    public static let registryVersion = "1.0.0"
    public static let helperIDs = [
        "stdlib.date_time",
        "stdlib.email",
        "stdlib.ip",
        "stdlib.url",
        "stdlib.uuid",
    ]

    public static func dateTime(_ stepID: String) -> SimplyStep {
        stdlibHelper(stepID, "stdlib.date_time", [:])
    }

    public static func email(_ stepID: String) -> SimplyStep {
        stdlibHelper(stepID, "stdlib.email", [:])
    }

    public static func ip(_ stepID: String, version: Int? = nil) -> SimplyStep {
        stdlibHelper(stepID, "stdlib.ip", ["version": version.map { $0 as Any } ?? NSNull()])
    }

    public static func url(_ stepID: String) -> SimplyStep {
        stdlibHelper(stepID, "stdlib.url", [:])
    }

    public static func uuid(_ stepID: String, version: Int? = nil) -> SimplyStep {
        stdlibHelper(stepID, "stdlib.uuid", ["version": version.map { $0 as Any } ?? NSNull()])
    }

}
