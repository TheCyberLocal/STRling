/**
 * STRling Validator - JSON Schema Validation for Target Artifacts
 *
 * This module provides validation functionality for STRling TargetArtifact objects
 * against their JSON Schema definitions (draft 2020-12). It ensures that compiled
 * patterns conform to the expected structure before emission.
 *
 * The validator uses the AJV library to validate artifacts against schemas located
 * in the spec/schema directory. It provides detailed error messages when validation
 * fails, helping to catch structural issues early in the compilation pipeline.
 */

import * as fs from "fs";
import Ajv2020 from "ajv/dist/2020";

// Note: Using 'ajv' library for JSON Schema validation (draft 2020-12)

/**
 * Error thrown when artifact validation fails.
 */
export class ValidationError extends Error {
    /**
     * Creates a new ValidationError.
     *
     * @param message - The error message describing the validation failure.
     */
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

/**
 * Validates a TargetArtifact against its JSON schema.
 *
 * Loads the appropriate schema from the spec/schema directory and validates
 * the artifact structure. Throws a ValidationError if validation fails.
 *
 * @param artifact - The TargetArtifact object to validate.
 * @param schemaPath - Path to the JSON schema file.
 * @throws ValidationError if the artifact doesn't conform to the schema.
 */
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
