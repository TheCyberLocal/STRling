import CSTRlingNative
import Foundation

public let interopProtocolVersion = "1.0.0"
public let nativeABIVersion: UInt32 = 1
public let maxInteropRequestBytes = 10_485_760
public let maxInteropResponseBytes = 33_554_432

public enum NativeErrorKind: String, Sendable {
    case load
    case abi
    case closed
    case transport
}

public struct NativeAdapterError: Error, CustomStringConvertible, Sendable {
    public let kind: NativeErrorKind
    public let detail: String
    public let status: UInt32?

    public init(kind: NativeErrorKind, detail: String, status: UInt32? = nil) {
        self.kind = kind
        self.detail = detail
        self.status = status
    }

    public var description: String {
        if let status { return "\(kind.rawValue): \(detail) (status \(status))" }
        return "\(kind.rawValue): \(detail)"
    }
}

public struct InteropProtocolError: Error, CustomStringConvertible, Sendable {
    public let code: String
    public let path: String
    public let operation: String?

    public var description: String { "\(code) at \(path)" }
}

public final class NativeClient: @unchecked Sendable {
    public let libraryPath: String

    private let lifecycle = NSCondition()
    private var handle: UnsafeMutableRawPointer?
    private var activeCalls = 0
    private var closed = false

    public init(libraryPath: String) throws {
        guard !libraryPath.isEmpty,
              URL(fileURLWithPath: libraryPath).path == libraryPath,
              FileManager.default.fileExists(atPath: libraryPath)
        else {
            throw NativeAdapterError(
                kind: .load,
                detail: "native STRling library path must be an existing absolute file"
            )
        }
        self.libraryPath = libraryPath
        var error = [CChar](repeating: 0, count: 512)
        let opened = libraryPath.withCString { pointer in
            error.withUnsafeMutableBufferPointer { buffer in
                strling_swift_native_open(pointer, buffer.baseAddress, buffer.count)
            }
        }
        guard let opened else {
            let detail = error.withUnsafeBufferPointer { buffer in
                String(cString: buffer.baseAddress!)
            }
            throw NativeAdapterError(kind: .load, detail: detail)
        }
        let actual = strling_swift_native_abi_version(opened)
        guard actual == nativeABIVersion else {
            strling_swift_native_close(opened)
            throw NativeAdapterError(
                kind: .abi,
                detail: "expected strling.c-abi \(nativeABIVersion)",
                status: actual
            )
        }
        handle = opened
    }

    deinit { close() }

    public var isClosed: Bool {
        lifecycle.lock()
        defer { lifecycle.unlock() }
        return closed
    }

    public func execute(_ request: [String: Any]) throws -> [String: Any] {
        guard JSONSerialization.isValidJSONObject(request) else {
            throw NativeAdapterError(kind: .transport, detail: "interop request is not strict JSON")
        }
        let encoded = try JSONSerialization.data(withJSONObject: request, options: [.sortedKeys])
        guard encoded.count <= maxInteropRequestBytes else {
            throw NativeAdapterError(
                kind: .transport,
                detail: "interop request exceeds \(maxInteropRequestBytes) bytes"
            )
        }
        let current = try beginCall()
        defer { endCall() }

        var output = strling_swift_owned_bytes(data: nil, len: 0)
        let result: Result<[String: Any], Error>
        do {
            let status = encoded.withUnsafeBytes { raw in
                strling_swift_native_execute(
                    current,
                    raw.bindMemory(to: UInt8.self).baseAddress,
                    encoded.count,
                    &output
                )
            }
            guard status == 0 else {
                throw NativeAdapterError(
                    kind: .abi,
                    detail: "native STRling execution failed",
                    status: status
                )
            }
            guard let data = output.data,
                  output.len > 0,
                  output.len <= maxInteropResponseBytes
            else {
                throw NativeAdapterError(
                    kind: .transport,
                    detail: "native STRling returned an invalid or oversized response"
                )
            }
            let copied = Data(bytes: data, count: output.len)
            result = .success(try Self.decodeResponse(copied))
        } catch {
            result = .failure(error)
        }
        let freeStatus = strling_swift_native_free(current, &output)
        if freeStatus != 0, case .success = result {
            throw NativeAdapterError(
                kind: .abi,
                detail: "native STRling response release failed",
                status: freeStatus
            )
        }
        return try result.get()
    }

    public func describe() throws -> Any {
        try completedResult(envelope("describe", [:]))
    }

    public func compile(
        _ compileRequest: [String: Any],
        targetProfile: [String: Any]? = nil
    ) throws -> Any {
        var payload: [String: Any] = ["compile_request": compileRequest]
        if let targetProfile { payload["target_profile"] = targetProfile }
        return try completedResult(envelope("compile", payload))
    }

    public func inspectTargetProfile(_ targetProfile: [String: Any]) throws -> Any {
        try completedResult(
            envelope("target_profile.inspect", ["target_profile": targetProfile])
        )
    }

    public func simplyCompile(
        _ builderRequest: [String: Any],
        targetProfile: [String: Any]? = nil
    ) throws -> Any {
        var payload: [String: Any] = ["builder_request": builderRequest]
        if let targetProfile { payload["target_profile"] = targetProfile }
        return try completedResult(envelope("simply.compile", payload))
    }

    public func close() {
        lifecycle.lock()
        if closed {
            lifecycle.unlock()
            return
        }
        closed = true
        while activeCalls != 0 { lifecycle.wait() }
        let current = handle
        handle = nil
        lifecycle.unlock()
        strling_swift_native_close(current)
    }

    private func beginCall() throws -> UnsafeMutableRawPointer {
        lifecycle.lock()
        defer { lifecycle.unlock() }
        guard !closed, let handle else {
            throw NativeAdapterError(kind: .closed, detail: "native STRling client is closed")
        }
        activeCalls += 1
        return handle
    }

    private func endCall() {
        lifecycle.lock()
        activeCalls -= 1
        if activeCalls == 0 { lifecycle.broadcast() }
        lifecycle.unlock()
    }

    private func completedResult(_ request: [String: Any]) throws -> Any {
        let response = try execute(request)
        if response["status"] as? String == "error",
           let body = response["error"] as? [String: Any],
           let code = body["code"] as? String,
           let path = body["path"] as? String
        {
            throw InteropProtocolError(
                code: code,
                path: path,
                operation: response["operation"] as? String
            )
        }
        guard let result = response["result"] else {
            throw NativeAdapterError(
                kind: .transport,
                detail: "completed interop response has no result"
            )
        }
        return result
    }

    private func envelope(_ operation: String, _ payload: [String: Any]) -> [String: Any] {
        [
            "interop_protocol_version": interopProtocolVersion,
            "operation": operation,
            "payload": payload,
        ]
    }

    private static func decodeResponse(_ data: Data) throws -> [String: Any] {
        let value: Any
        do {
            guard String(data: data, encoding: .utf8) != nil else {
                throw NativeAdapterError(
                    kind: .transport,
                    detail: "native STRling response is not UTF-8"
                )
            }
            value = try JSONSerialization.jsonObject(with: data, options: [])
            var validator = JSONDuplicateKeyValidator(data)
            try validator.validate()
        } catch {
            throw NativeAdapterError(
                kind: .transport,
                detail: "native STRling response is not strict UTF-8 JSON: \(error)"
            )
        }
        guard let response = value as? [String: Any],
              response["interop_protocol_version"] as? String == interopProtocolVersion,
              let status = response["status"] as? String,
              status == "completed" || status == "error"
        else {
            throw NativeAdapterError(
                kind: .transport,
                detail: "interop response has an unsupported version or status"
            )
        }
        if status == "completed", response["result"] == nil {
            throw NativeAdapterError(
                kind: .transport,
                detail: "completed interop response has no result"
            )
        }
        if status == "error" {
            guard let body = response["error"] as? [String: Any],
                  body["code"] is String,
                  body["path"] is String
            else {
                throw NativeAdapterError(
                    kind: .transport,
                    detail: "failed interop response has no stable code and path"
                )
            }
        }
        return response
    }
}

private struct JSONDuplicateKeyValidator {
    private let bytes: [UInt8]
    private var index = 0

    init(_ data: Data) { bytes = Array(data) }

    mutating func validate() throws {
        skipWhitespace()
        try value()
        skipWhitespace()
        guard index == bytes.count else { throw ValidationError.trailingContent }
    }

    private mutating func value() throws {
        skipWhitespace()
        guard index < bytes.count else { throw ValidationError.missingValue }
        switch bytes[index] {
        case 0x7b: try object()
        case 0x5b: try array()
        case 0x22: _ = try string()
        default:
            while index < bytes.count,
                  ![0x2c, 0x5d, 0x7d, 0x20, 0x09, 0x0a, 0x0d].contains(bytes[index])
            {
                index += 1
            }
        }
    }

    private mutating func object() throws {
        index += 1
        skipWhitespace()
        var names = Set<String>()
        if take(0x7d) { return }
        while true {
            skipWhitespace()
            let name = try string()
            guard names.insert(name).inserted else {
                throw ValidationError.duplicateProperty(name)
            }
            skipWhitespace()
            try expect(0x3a)
            try value()
            skipWhitespace()
            if take(0x7d) { return }
            try expect(0x2c)
        }
    }

    private mutating func array() throws {
        index += 1
        skipWhitespace()
        if take(0x5d) { return }
        while true {
            try value()
            skipWhitespace()
            if take(0x5d) { return }
            try expect(0x2c)
        }
    }

    private mutating func string() throws -> String {
        let start = index
        try expect(0x22)
        var escaped = false
        while index < bytes.count {
            let character = bytes[index]
            index += 1
            if escaped {
                escaped = false
            } else if character == 0x5c {
                escaped = true
            } else if character == 0x22 {
                return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index]))
            }
        }
        throw ValidationError.unterminatedString
    }

    private mutating func skipWhitespace() {
        while index < bytes.count, [0x20, 0x09, 0x0a, 0x0d].contains(bytes[index]) {
            index += 1
        }
    }

    private mutating func take(_ expected: UInt8) -> Bool {
        guard index < bytes.count, bytes[index] == expected else { return false }
        index += 1
        return true
    }

    private mutating func expect(_ expected: UInt8) throws {
        guard take(expected) else { throw ValidationError.unexpectedToken(expected) }
    }

    private enum ValidationError: Error {
        case duplicateProperty(String)
        case missingValue
        case trailingContent
        case unexpectedToken(UInt8)
        case unterminatedString
    }
}
