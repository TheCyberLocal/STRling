// Generated from the canonical standard-library registry. Do not edit.
// These lexical helpers record Simply recipes; they do not validate semantics.
import Foundation

public enum Essential {
    public static let sourceSHA256 = "db3d1fc6ddd1b0ef83cb7bfb4a9bd84c8bcc547d5a6649a6747cc4b94fb4edff"
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
