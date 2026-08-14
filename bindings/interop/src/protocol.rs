use std::fmt;
use std::io::{self, Write};

use serde::de::DeserializeOwned;
use serde::Serialize;
use serde_json::{Map, Value};
use strling_kernel::protocol::CompileRequest;
use strling_kernel::simply::{
    decode_simply_builder_request, replay_simply_builder_request,
    supported_simply_protocol_version, SimplyAdapterResponse, SimplyBuilderRequestDecodeError,
    SIMPLY_PROTOCOL_VERSION,
};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::Validate;

pub const INTEROP_PROTOCOL_VERSION: &str = "1.0.0";
pub const MAX_INTEROP_REQUEST_BYTES: usize = 10_485_760;
pub const MAX_INTEROP_RESPONSE_BYTES: usize = 33_554_432;

const ABI_DESCRIPTOR: &str = include_str!("../../../spec/interop/1.0/abi.json");

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Operation {
    Describe,
    Compile,
    TargetProfileInspect,
    SimplyCompile,
}

impl Operation {
    const fn as_str(self) -> &'static str {
        match self {
            Self::Describe => "describe",
            Self::Compile => "compile",
            Self::TargetProfileInspect => "target_profile.inspect",
            Self::SimplyCompile => "simply.compile",
        }
    }

    fn parse(value: &str) -> Option<Self> {
        match value {
            "describe" => Some(Self::Describe),
            "compile" => Some(Self::Compile),
            "target_profile.inspect" => Some(Self::TargetProfileInspect),
            "simply.compile" => Some(Self::SimplyCompile),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum InteropErrorCode {
    InvalidUtf8,
    InvalidJson,
    InvalidEnvelope,
    UnsupportedProtocolVersion,
    UnsupportedOperation,
    RequestTooLarge,
    InvalidPayload,
    CanonicalBoundaryFailure,
    ResponseTooLarge,
    SerializationFailure,
}

impl InteropErrorCode {
    const fn as_str(self) -> &'static str {
        match self {
            Self::InvalidUtf8 => "STRL-INTEROP-0001",
            Self::InvalidJson => "STRL-INTEROP-0002",
            Self::InvalidEnvelope => "STRL-INTEROP-0003",
            Self::UnsupportedProtocolVersion => "STRL-INTEROP-0004",
            Self::UnsupportedOperation => "STRL-INTEROP-0005",
            Self::RequestTooLarge => "STRL-INTEROP-0006",
            Self::InvalidPayload => "STRL-INTEROP-0007",
            Self::CanonicalBoundaryFailure => "STRL-INTEROP-0008",
            Self::ResponseTooLarge => "STRL-INTEROP-0009",
            Self::SerializationFailure => "STRL-INTEROP-0010",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct InteropFailure {
    code: InteropErrorCode,
    path: &'static str,
    operation: Option<Operation>,
}

impl InteropFailure {
    const fn new(code: InteropErrorCode, path: &'static str) -> Self {
        Self {
            code,
            path,
            operation: None,
        }
    }

    const fn for_operation(mut self, operation: Operation) -> Self {
        self.operation = Some(operation);
        self
    }
}

#[derive(Serialize)]
struct CompletedResponse<'a, T: Serialize> {
    interop_protocol_version: &'static str,
    operation: &'static str,
    status: &'static str,
    result: &'a T,
}

#[derive(Serialize)]
struct ErrorResponse {
    interop_protocol_version: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    operation: Option<&'static str>,
    status: &'static str,
    error: ErrorDetail,
}

#[derive(Serialize)]
struct ErrorDetail {
    code: &'static str,
    path: &'static str,
}

#[derive(Serialize)]
struct ProfileInspection<'a> {
    profile_reference: strling_kernel::target::TargetProfileReference,
    target_profile: &'a TargetProfile,
}

#[derive(Debug, Eq, PartialEq)]
enum BoundedSerializationError {
    Limit,
    Serialization,
}

impl fmt::Display for BoundedSerializationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Limit => formatter.write_str("serialized response exceeds its byte limit"),
            Self::Serialization => formatter.write_str("response serialization failed"),
        }
    }
}

struct LimitedWriter {
    bytes: Vec<u8>,
    limit: usize,
    exceeded: bool,
}

impl LimitedWriter {
    fn new(limit: usize) -> Self {
        Self {
            bytes: Vec::new(),
            limit,
            exceeded: false,
        }
    }
}

impl Write for LimitedWriter {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        let next = self.bytes.len().checked_add(buffer.len());
        if next.map_or(true, |length| length > self.limit) {
            self.exceeded = true;
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "STRling interop response limit exceeded",
            ));
        }
        self.bytes.extend_from_slice(buffer);
        Ok(buffer.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

/// Execute one bounded `strling.interop` request and return one response object.
///
/// This safe function is the sole dispatcher used by native and WebAssembly
/// raw-memory edges. It retains no pointer or mutable global state.
#[must_use]
pub fn execute_bytes(request: &[u8]) -> Vec<u8> {
    match dispatch(request) {
        Ok(response) => response,
        Err(failure) => serialize_failure(failure),
    }
}

fn dispatch(request: &[u8]) -> Result<Vec<u8>, InteropFailure> {
    if request.len() > MAX_INTEROP_REQUEST_BYTES {
        return Err(InteropFailure::new(InteropErrorCode::RequestTooLarge, "$"));
    }
    let text = std::str::from_utf8(request)
        .map_err(|_| InteropFailure::new(InteropErrorCode::InvalidUtf8, "$"))?;
    let value: Value = serde_json::from_str(text)
        .map_err(|_| InteropFailure::new(InteropErrorCode::InvalidJson, "$"))?;
    let mut envelope = match value {
        Value::Object(object) => object,
        _ => return Err(InteropFailure::new(InteropErrorCode::InvalidEnvelope, "$")),
    };

    let version = required_string(
        &mut envelope,
        "interop_protocol_version",
        "$.interop_protocol_version",
    )?;
    if version != INTEROP_PROTOCOL_VERSION {
        return Err(InteropFailure::new(
            InteropErrorCode::UnsupportedProtocolVersion,
            "$.interop_protocol_version",
        ));
    }
    let operation_text = required_string(&mut envelope, "operation", "$.operation")?;
    let Some(operation) = Operation::parse(&operation_text) else {
        return Err(InteropFailure::new(
            InteropErrorCode::UnsupportedOperation,
            "$.operation",
        ));
    };
    let payload = envelope.remove("payload").ok_or_else(|| {
        InteropFailure::new(InteropErrorCode::InvalidEnvelope, "$.payload").for_operation(operation)
    })?;
    if !envelope.is_empty() {
        return Err(
            InteropFailure::new(InteropErrorCode::InvalidEnvelope, "$").for_operation(operation)
        );
    }

    match operation {
        Operation::Describe => dispatch_describe(payload),
        Operation::Compile => dispatch_compile(payload),
        Operation::TargetProfileInspect => dispatch_profile_inspect(payload),
        Operation::SimplyCompile => dispatch_simply(payload),
    }
}

fn dispatch_describe(payload: Value) -> Result<Vec<u8>, InteropFailure> {
    let operation = Operation::Describe;
    let object = payload_object(payload, operation)?;
    if !object.is_empty() {
        return Err(invalid_payload("$.payload", operation));
    }
    let descriptor: Value = serde_json::from_str(ABI_DESCRIPTOR).map_err(|_| {
        InteropFailure::new(InteropErrorCode::SerializationFailure, "$").for_operation(operation)
    })?;
    Ok(serialize_completed(operation, &descriptor))
}

fn dispatch_compile(payload: Value) -> Result<Vec<u8>, InteropFailure> {
    let operation = Operation::Compile;
    let mut object = payload_object(payload, operation)?;
    let request = deserialize_required::<CompileRequest>(
        &mut object,
        "compile_request",
        "$.payload.compile_request",
        operation,
    )?;
    let target_profile = deserialize_optional::<TargetProfile>(
        &mut object,
        "target_profile",
        "$.payload.target_profile",
        operation,
    )?;
    reject_extra_payload(&object, operation)?;
    let result = strling_kernel::compile(&request, target_profile.as_ref()).map_err(|_| {
        InteropFailure::new(InteropErrorCode::CanonicalBoundaryFailure, "$.payload")
            .for_operation(operation)
    })?;
    Ok(serialize_completed(operation, &result))
}

fn dispatch_profile_inspect(payload: Value) -> Result<Vec<u8>, InteropFailure> {
    let operation = Operation::TargetProfileInspect;
    let mut object = payload_object(payload, operation)?;
    let target_profile = deserialize_required::<TargetProfile>(
        &mut object,
        "target_profile",
        "$.payload.target_profile",
        operation,
    )?;
    reject_extra_payload(&object, operation)?;
    target_profile.validate().map_err(|_| {
        InteropFailure::new(
            InteropErrorCode::CanonicalBoundaryFailure,
            "$.payload.target_profile",
        )
        .for_operation(operation)
    })?;
    let profile_reference = target_profile.reference().map_err(|_| {
        InteropFailure::new(
            InteropErrorCode::CanonicalBoundaryFailure,
            "$.payload.target_profile",
        )
        .for_operation(operation)
    })?;
    let result = ProfileInspection {
        profile_reference,
        target_profile: &target_profile,
    };
    Ok(serialize_completed(operation, &result))
}

fn dispatch_simply(payload: Value) -> Result<Vec<u8>, InteropFailure> {
    let operation = Operation::SimplyCompile;
    let mut object = payload_object(payload, operation)?;
    let builder_value = object
        .remove("builder_request")
        .ok_or_else(|| invalid_payload("$.payload.builder_request", operation))?;
    let target_profile = deserialize_optional::<TargetProfile>(
        &mut object,
        "target_profile",
        "$.payload.target_profile",
        operation,
    )?;
    reject_extra_payload(&object, operation)?;
    let builder_json = serde_json::to_string(&builder_value).map_err(|_| {
        InteropFailure::new(
            InteropErrorCode::SerializationFailure,
            "$.payload.builder_request",
        )
        .for_operation(operation)
    })?;
    let response_version = supported_simply_protocol_version(&builder_json)
        .unwrap_or(SIMPLY_PROTOCOL_VERSION)
        .to_owned();
    let builder_request = match decode_simply_builder_request(&builder_json) {
        Ok(request) => request,
        Err(SimplyBuilderRequestDecodeError::Construction(errors)) => {
            let response = SimplyAdapterResponse::Failure {
                protocol_version: response_version,
                errors: errors.errors,
            };
            return Ok(serialize_completed(operation, &response));
        }
        Err(SimplyBuilderRequestDecodeError::Malformed(_)) => {
            return Err(invalid_payload("$.payload.builder_request", operation));
        }
    };
    let response_version = builder_request.protocol_version().to_owned();
    let request = match replay_simply_builder_request(builder_request) {
        Ok(request) => request,
        Err(errors) => {
            let response = SimplyAdapterResponse::Failure {
                protocol_version: response_version,
                errors: errors.errors,
            };
            return Ok(serialize_completed(operation, &response));
        }
    };
    let result = strling_kernel::compile(&request, target_profile.as_ref()).map_err(|_| {
        InteropFailure::new(InteropErrorCode::CanonicalBoundaryFailure, "$.payload")
            .for_operation(operation)
    })?;
    let response = SimplyAdapterResponse::Success {
        protocol_version: response_version,
        compile_request: request,
        compile_result: result,
    };
    Ok(serialize_completed(operation, &response))
}

fn required_string(
    object: &mut Map<String, Value>,
    key: &str,
    path: &'static str,
) -> Result<String, InteropFailure> {
    match object.remove(key) {
        Some(Value::String(value)) => Ok(value),
        _ => Err(InteropFailure::new(InteropErrorCode::InvalidEnvelope, path)),
    }
}

fn payload_object(
    payload: Value,
    operation: Operation,
) -> Result<Map<String, Value>, InteropFailure> {
    match payload {
        Value::Object(object) => Ok(object),
        _ => Err(invalid_payload("$.payload", operation)),
    }
}

fn deserialize_required<T: DeserializeOwned>(
    object: &mut Map<String, Value>,
    key: &str,
    path: &'static str,
    operation: Operation,
) -> Result<T, InteropFailure> {
    let value = object
        .remove(key)
        .ok_or_else(|| invalid_payload(path, operation))?;
    serde_json::from_value(value).map_err(|_| invalid_payload(path, operation))
}

fn deserialize_optional<T: DeserializeOwned>(
    object: &mut Map<String, Value>,
    key: &str,
    path: &'static str,
    operation: Operation,
) -> Result<Option<T>, InteropFailure> {
    object
        .remove(key)
        .map(|value| serde_json::from_value(value).map_err(|_| invalid_payload(path, operation)))
        .transpose()
}

fn reject_extra_payload(
    object: &Map<String, Value>,
    operation: Operation,
) -> Result<(), InteropFailure> {
    if object.is_empty() {
        Ok(())
    } else {
        Err(invalid_payload("$.payload", operation))
    }
}

const fn invalid_payload(path: &'static str, operation: Operation) -> InteropFailure {
    InteropFailure::new(InteropErrorCode::InvalidPayload, path).for_operation(operation)
}

fn serialize_completed<T: Serialize>(operation: Operation, result: &T) -> Vec<u8> {
    let response = CompletedResponse {
        interop_protocol_version: INTEROP_PROTOCOL_VERSION,
        operation: operation.as_str(),
        status: "completed",
        result,
    };
    match serialize_bounded(&response, MAX_INTEROP_RESPONSE_BYTES) {
        Ok(bytes) => bytes,
        Err(BoundedSerializationError::Limit) => serialize_failure(
            InteropFailure::new(InteropErrorCode::ResponseTooLarge, "$").for_operation(operation),
        ),
        Err(BoundedSerializationError::Serialization) => serialize_failure(
            InteropFailure::new(InteropErrorCode::SerializationFailure, "$")
                .for_operation(operation),
        ),
    }
}

fn serialize_failure(failure: InteropFailure) -> Vec<u8> {
    let response = ErrorResponse {
        interop_protocol_version: INTEROP_PROTOCOL_VERSION,
        operation: failure.operation.map(Operation::as_str),
        status: "error",
        error: ErrorDetail {
            code: failure.code.as_str(),
            path: failure.path,
        },
    };
    serde_json::to_vec(&response).unwrap_or_else(|_| {
        br#"{"interop_protocol_version":"1.0.0","status":"error","error":{"code":"STRL-INTEROP-0010","path":"$"}}"#.to_vec()
    })
}

fn serialize_bounded<T: Serialize>(
    value: &T,
    limit: usize,
) -> Result<Vec<u8>, BoundedSerializationError> {
    let mut writer = LimitedWriter::new(limit);
    if serde_json::to_writer(&mut writer, value).is_err() {
        return if writer.exceeded {
            Err(BoundedSerializationError::Limit)
        } else {
            Err(BoundedSerializationError::Serialization)
        };
    }
    Ok(writer.bytes)
}

#[cfg(test)]
mod tests {
    use serde::ser::Error as _;
    use serde::{Serialize, Serializer};
    use serde_json::json;

    use super::*;

    struct SerializationFailure;

    impl Serialize for SerializationFailure {
        fn serialize<S: Serializer>(&self, _serializer: S) -> Result<S::Ok, S::Error> {
            Err(S::Error::custom("controlled serialization failure"))
        }
    }

    #[test]
    fn response_limit_and_serialization_failures_are_distinct() {
        assert_eq!(
            Err(BoundedSerializationError::Limit),
            serialize_bounded(&json!({"large": "0123456789"}), 5)
        );
        assert_eq!(
            Err(BoundedSerializationError::Serialization),
            serialize_bounded(&SerializationFailure, 1024)
        );
    }

    #[test]
    fn error_response_fallback_is_valid_json() {
        let response = serialize_failure(InteropFailure::new(
            InteropErrorCode::SerializationFailure,
            "$",
        ));
        let value: Value = serde_json::from_slice(&response).expect("valid JSON response");
        assert_eq!("STRL-INTEROP-0010", value["error"]["code"]);
    }
}
