package com.strling.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.*;

import java.io.IOException;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * STRling Validator - JSON Schema Validation for Target Artifacts.
 * 
 * <p>This module provides validation functionality for STRling TargetArtifact objects
 * against their JSON Schema definitions (draft 2020-12). It ensures that compiled
 * patterns conform to the expected structure before emission.</p>
 * 
 * <p>The validator uses the json-schema-validator library to validate artifacts against schemas
 * located in the spec/schema directory. It provides detailed error messages when
 * validation fails, helping to catch structural issues early in the compilation
 * pipeline.</p>
 */
public class Validator {
    
    private static final ObjectMapper objectMapper = new ObjectMapper();
    
    /**
     * Custom exception for JSON schema validation errors.
     */
    public static class ValidationError extends RuntimeException {
        public ValidationError(String message) {
            super(message);
        }
        
        public ValidationError(String message, Throwable cause) {
            super(message, cause);
        }
    }
    
    /**
     * Validate a TargetArtifact against a JSON Schema (draft 2020-12).
     * 
     * <p>This method validates the provided artifact against the schema at the specified
     * path. It uses JSON Schema Draft 2020-12 for validation and handles local schema
     * references properly.</p>
     *
     * @param artifact The concrete artifact to validate (as a Map)
     * @param schemaPath Filesystem path to the JSON schema (can contain $ref)
     * @throws ValidationError If validation fails
     */
    public static void validateArtifact(Map<String, Object> artifact, String schemaPath) {
        try {
            // Read the schema file
            String schemaContent = new String(Files.readAllBytes(Paths.get(schemaPath)));
            
            // Get the directory containing the schema for resolving relative refs
            Path schemaDir = Paths.get(schemaPath).getParent();
            
            // Create mappings for schema URIs to local files
            Map<String, String> schemaMap = new HashMap<>();
            schemaMap.put("https://strling.dev/schema/base.schema.json", 
                         schemaDir.resolve("base.schema.json").toString());
            schemaMap.put("https://strling.dev/schema/pcre2.v1.schema.json", 
                         schemaDir.resolve("pcre2.v1.schema.json").toString());
            
            // Create a JsonSchemaFactory with URI mappings
            JsonSchemaFactory factory = JsonSchemaFactory.builder(
                JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012))
                .schemaMappers(schemaMappers -> {
                    schemaMappers.mapPrefix("https://strling.dev/schema/", 
                                          "file://" + schemaDir.toString() + "/");
                })
                .build();
            
            // Parse the schema - pass the URI of the schema for proper reference resolution
            URI schemaUri = Paths.get(schemaPath).toUri();
            JsonNode schemaNode = objectMapper.readTree(schemaContent);
            SchemaValidatorsConfig config = new SchemaValidatorsConfig();
            JsonSchema schema = factory.getSchema(schemaUri, schemaNode, config);
            
            // Convert the artifact to JsonNode
            JsonNode artifactNode = objectMapper.valueToTree(artifact);
            
            // Validate
            Set<ValidationMessage> errors = schema.validate(artifactNode);
            
            // If there are validation errors, throw an exception with details
            if (!errors.isEmpty()) {
                StringBuilder errorMessage = new StringBuilder("JSON Schema validation failed:\n");
                for (ValidationMessage error : errors) {
                    errorMessage.append("  - ").append(error.getMessage()).append("\n");
                }
                throw new ValidationError(errorMessage.toString().trim());
            }
            
        } catch (IOException e) {
            throw new ValidationError("Failed to read schema file: " + schemaPath, e);
        } catch (ValidationError e) {
            throw e;
        } catch (Exception e) {
            throw new ValidationError("Validation error: " + e.getMessage(), e);
        }
    }
}
