/**
 * @file essential_5.test.ts
 *
 * Conformance tests for the Simply standard library "Essential 5" patterns:
 * email, url, uuid, ip, and dateTime. The fixtures defined in
 * `spec/stdlib/essential_5.json` are the cross-binding source of truth — every
 * binding's implementation must satisfy the same valid/invalid expectations.
 */

import * as s from "../../src/STRling/simply";
import * as fs from "fs";
import * as path from "path";

const SPEC_PATH = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "..",
    "spec",
    "stdlib",
    "essential_5.json",
);

const spec = JSON.parse(fs.readFileSync(SPEC_PATH, "utf8"));

function fullMatcher(pattern: { toString(): string }): RegExp {
    return new RegExp("^(?:" + String(pattern) + ")$");
}

describe("Simply Essential 5 — Standard Library", () => {
    describe("email()", () => {
        const re = fullMatcher(s.email());
        for (const v of spec.patterns.email.fixtures.valid) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.email.fixtures.invalid) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });

    describe("url()", () => {
        const re = fullMatcher(s.url());
        for (const v of spec.patterns.url.fixtures.valid) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.url.fixtures.invalid) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });

    describe("uuid() — generic 8-4-4-4-12", () => {
        const re = fullMatcher(s.uuid());
        for (const v of spec.patterns.uuid.fixtures.valid_default) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.uuid.fixtures.invalid_default) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });

    describe("uuid(4) — RFC 4122 v4", () => {
        const re = fullMatcher(s.uuid(4));
        for (const v of spec.patterns.uuid.fixtures.valid_v4) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.uuid.fixtures.invalid_v4) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });

    describe("ip(4) — IPv4 dot-decimal", () => {
        const re = fullMatcher(s.ip(4));
        for (const v of spec.patterns.ip.fixtures.valid_v4) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.ip.fixtures.invalid_v4) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });

    describe("ip(6) — IPv6 colon-hex (full form)", () => {
        const re = fullMatcher(s.ip(6));
        for (const v of spec.patterns.ip.fixtures.valid_v6) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.ip.fixtures.invalid_v6) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });

    describe("ip() — accepts both families", () => {
        const re = fullMatcher(s.ip());
        for (const v of [
            ...spec.patterns.ip.fixtures.valid_v4,
            ...spec.patterns.ip.fixtures.valid_v6,
        ]) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
    });

    describe("dateTime() — ISO 8601 / RFC 3339", () => {
        const re = fullMatcher(s.dateTime());
        for (const v of spec.patterns.dateTime.fixtures.valid) {
            test(`accepts ${v}`, () => expect(re.test(v)).toBe(true));
        }
        for (const i of spec.patterns.dateTime.fixtures.invalid) {
            test(`rejects ${i}`, () => expect(re.test(i)).toBe(false));
        }
    });
});
