import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
    canonicalStdlib,
    dateTime,
    email,
    ip,
    url,
    uuid,
} from "../../src/STRling/simply/index.js";

describe("canonical standard-library registry surface", () => {
    test("delegates all five helpers through Simply requests", () => {
        const essential_5 = JSON.parse(
            readFileSync(
                resolve(process.cwd(), "../../spec/stdlib/essential_5.json"),
                "utf8",
            ),
        ) as { patterns: Record<string, unknown> };
        const requests = [dateTime(), email(), ip(), url(), uuid()].map(
            (helper) =>
                helper.buildRequest({
                    requested_outputs: ["semantic"],
                    compiler_options: {
                        partial_semantics: "forbid",
                        diagnostic_policy: { minimum_severity: "hint" },
                    },
                }),
        ) as { steps: { arguments: { helper_id: string } }[] }[];

        expect(
            requests.map((request) => request.steps[0].arguments.helper_id),
        ).toEqual([...canonicalStdlib.STDLIB_HELPER_IDS]);
        expect(Object.keys(essential_5.patterns).sort()).toEqual([
            "dateTime",
            "email",
            "ip",
            "url",
            "uuid",
        ]);
    });
});
