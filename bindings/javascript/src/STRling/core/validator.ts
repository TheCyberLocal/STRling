/**
 * STRling v3 — Validator
 * Validates TargetArtifact against JSON Schema (draft 2020-12).
 *
 * Ported from Python reference implementation.
 */

import * as fs from "fs";
import Ajv2020 from "ajv/dist/2020.js";

// Note: Using 'ajv' library for JSON Schema validation (draft 2020-12)

export class ValidationError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "ValidationError";
    }
}

// Create a shared AJV instance to avoid duplicate schema registration
const ajv = new Ajv2020({
    strict: false,
    allErrors: true,
    verbose: true,
});

const loadedSchemas = new Set<string>();

export function validateArtifact(
    artifact: any,
    schemaPath: string,
    registry: any = null
): boolean {
    /**
     * Validate a TargetArtifact against a JSON Schema (draft 2020-12).
     *
     * @param {object} artifact - The concrete artifact to validate
     * @param {string} schemaPath - Filesystem path to the JSON schema
     * @param {object} registry - Optional registry to resolve $ref (currently unused, for future compatibility)
     * @throws {ValidationError} If validation fails
     */

    // Read the schema file
    const schemaText = fs.readFileSync(schemaPath, "utf-8");
    const schema = JSON.parse(schemaText);

    // Add base schema to handle $ref if needed
    // Determine if we need to load the base schema
    const schemaDir = schemaPath.substring(0, schemaPath.lastIndexOf("/"));
    const baseSchemaPath = schemaDir + "/base.schema.json";

    // Check if the schema has a reference to base.schema.json
    if (
        JSON.stringify(schema).includes("base.schema.json") &&
        !loadedSchemas.has(baseSchemaPath)
    ) {
        try {
            const baseSchemaText = fs.readFileSync(baseSchemaPath, "utf-8");
            const baseSchema = JSON.parse(baseSchemaText);
            // Add the base schema with its $id so references can be resolved
            if (baseSchema.$id && !ajv.getSchema(baseSchema.$id)) {
                ajv.addSchema(baseSchema);
            }
            loadedSchemas.add(baseSchemaPath);
        } catch (e) {
            // If base schema doesn't exist, continue without it
        }
    }

    // Compile and validate (compile will auto-add the schema if it has an $id)
    let validate;
    if (schema.$id && ajv.getSchema(schema.$id)) {
        validate = ajv.getSchema(schema.$id)!;
    } else {
        validate = ajv.compile(schema);
    }

    const valid = validate(artifact);

    if (!valid) {
        // Construct error message from validation errors
        if (validate.errors && validate.errors.length > 0) {
            const error = validate.errors[0];
            // Use the raw error message from ajv which matches the expected format
            const message = error.message || "Validation failed";
            throw new ValidationError(message);
        }
        throw new ValidationError("Validation failed");
    }

    return true;
}
