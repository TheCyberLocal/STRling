#!/usr/bin/env node

"use strict";

const PROTOCOL_VERSION = "1.0.0";
const MAXIMUM_INPUT_BYTES = 4 * 1024 * 1024;
const MAXIMUM_CASES = 1024;
const MAXIMUM_SUBJECTS_PER_CASE = 32;
const MAXIMUM_SOURCE_BYTES = 64 * 1024;
const MAXIMUM_SUBJECT_CODE_UNITS = 1024 * 1024;
const MAXIMUM_MATCHES = 1024;

function requireRecord(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  return value;
}

function requireString(value, label) {
  if (typeof value !== "string") {
    throw new TypeError(`${label} must be a string`);
  }
  return value;
}

function requireStringArray(value, label) {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new TypeError(`${label} must be an array of strings`);
  }
  return value;
}

function boundedCase(rawCase) {
  const item = requireRecord(rawCase, "case");
  const id = requireString(item.id, "case.id");
  const source = requireString(item.source, `${id}.source`);
  const flags = requireStringArray(item.flags, `${id}.flags`);
  const mode = item.mode === undefined ? "exec" : requireString(item.mode, `${id}.mode`);
  if (mode !== "exec" && mode !== "iterate") {
    throw new RangeError(`${id}.mode is unsupported`);
  }
  if (Buffer.byteLength(source, "utf8") > MAXIMUM_SOURCE_BYTES) {
    throw new RangeError(`${id}.source exceeds the byte limit`);
  }
  const subjects = item.subjects === undefined
    ? []
    : requireStringArray(item.subjects, `${id}.subjects`);
  if (subjects.length > MAXIMUM_SUBJECTS_PER_CASE) {
    throw new RangeError(`${id}.subjects exceeds the count limit`);
  }
  if (subjects.some((subject) => subject.length > MAXIMUM_SUBJECT_CODE_UNITS)) {
    throw new RangeError(`${id}.subject exceeds the UTF-16 limit`);
  }
  const captureNames = item.capture_names === undefined
    ? {}
    : requireRecord(item.capture_names, `${id}.capture_names`);
  for (const [slot, name] of Object.entries(captureNames)) {
    if (!/^(0|[1-9][0-9]*)$/.test(slot) || typeof name !== "string") {
      throw new TypeError(`${id}.capture_names is malformed`);
    }
  }
  const maximumMatches = item.maximum_matches === undefined
    ? 1
    : item.maximum_matches;
  if (!Number.isSafeInteger(maximumMatches) || maximumMatches < 1 || maximumMatches > MAXIMUM_MATCHES) {
    throw new RangeError(`${id}.maximum_matches is outside the limit`);
  }
  return {id, source, flags, mode, subjects, captureNames, maximumMatches};
}

function addFlag(flags, flag) {
  return flags.includes(flag) ? flags : `${flags}${flag}`;
}

function compile(item, instrumented) {
  let flags = item.flags.join("");
  if (item.mode === "iterate") {
    flags = addFlag(flags, "g");
  }
  if (instrumented) {
    flags = addFlag(flags, "d");
  }
  return new RegExp(item.source, flags);
}

function assertParity(baseline, instrumented, caseId) {
  if ((baseline === null) !== (instrumented === null)) {
    throw new Error(`${caseId}: index instrumentation changed match presence`);
  }
  if (baseline === null) {
    return;
  }
  if (baseline.index !== instrumented.index || baseline.length !== instrumented.length) {
    throw new Error(`${caseId}: index instrumentation changed match shape`);
  }
  for (let index = 0; index < baseline.length; index += 1) {
    if (baseline[index] !== instrumented[index]) {
      throw new Error(`${caseId}: index instrumentation changed capture values`);
    }
  }
}

function projectMatch(match, captureNames) {
  const captures = [];
  for (let index = 0; index < match.length; index += 1) {
    const rawSpan = match.indices[index];
    const capture = {
      index,
      span: rawSpan === undefined ? null : [rawSpan[0], rawSpan[1]],
      value: match[index] === undefined ? null : match[index],
    };
    const key = String(index);
    if (Object.prototype.hasOwnProperty.call(captureNames, key)) {
      capture.name = captureNames[key];
    }
    captures.push(capture);
  }
  return {
    span: [match.indices[0][0], match.indices[0][1]],
    value: match[0],
    captures,
  };
}

function advanceStringIndex(subject, index, unicode) {
  if (!unicode || index + 1 >= subject.length) {
    return index + 1;
  }
  const first = subject.charCodeAt(index);
  if (first < 0xd800 || first > 0xdbff) {
    return index + 1;
  }
  const second = subject.charCodeAt(index + 1);
  return second >= 0xdc00 && second <= 0xdfff ? index + 2 : index + 1;
}

function observeSubject(item, baseline, instrumented, subject) {
  baseline.lastIndex = 0;
  instrumented.lastIndex = 0;
  const matches = [];
  const unicode = item.flags.includes("u") || item.flags.includes("v");
  while (true) {
    const plain = baseline.exec(subject);
    const detailed = instrumented.exec(subject);
    assertParity(plain, detailed, item.id);
    if (detailed === null) {
      break;
    }
    if (matches.length >= item.maximumMatches) {
      throw new RangeError(`${item.id}: match count exceeds the governed limit`);
    }
    matches.push(projectMatch(detailed, item.captureNames));
    if (item.mode !== "iterate") {
      break;
    }
    if (detailed[0] === "") {
      const next = advanceStringIndex(subject, instrumented.lastIndex, unicode);
      baseline.lastIndex = next;
      instrumented.lastIndex = next;
    }
  }
  return {subject, matches};
}

function runCase(rawCase) {
  const item = boundedCase(rawCase);
  let baseline;
  let instrumented;
  try {
    baseline = compile(item, false);
    instrumented = compile(item, true);
  } catch (error) {
    if (error instanceof SyntaxError) {
      return {id: item.id, compile: "syntax_error", observations: []};
    }
    throw error;
  }
  return {
    id: item.id,
    compile: "ok",
    observations: item.subjects.map((subject) =>
      observeSubject(item, baseline, instrumented, subject)),
  };
}

async function readRequest() {
  const chunks = [];
  let byteLength = 0;
  for await (const chunk of process.stdin) {
    byteLength += chunk.length;
    if (byteLength > MAXIMUM_INPUT_BYTES) {
      throw new RangeError("request exceeds the byte limit");
    }
    chunks.push(chunk);
  }
  const request = requireRecord(JSON.parse(Buffer.concat(chunks).toString("utf8")), "request");
  if (request.protocol_version !== PROTOCOL_VERSION) {
    throw new RangeError("unsupported protocol version");
  }
  if (!Array.isArray(request.cases) || request.cases.length > MAXIMUM_CASES) {
    throw new RangeError("request.cases exceeds the count limit");
  }
  return request;
}

try {
  const request = await readRequest();
  const result = {
    protocol_version: PROTOCOL_VERSION,
    runtime: {
      node: process.version,
      v8: process.versions.v8,
      platform: process.platform,
      architecture: process.arch,
    },
    cases: request.cases.map(runCase),
  };
  process.stdout.write(`${JSON.stringify(result)}\n`);
} catch (error) {
  const name = error instanceof Error ? error.name : "Error";
  process.stderr.write(`${JSON.stringify({protocol_version: PROTOCOL_VERSION, fatal: {code: "HARNESS_ERROR", name}})}\n`);
  process.exitCode = 1;
}
