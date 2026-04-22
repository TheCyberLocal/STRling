package com.strling;

import com.strling.simply.Essential;
import com.strling.simply.Simply;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.util.regex.Pattern;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import static org.junit.jupiter.api.Assertions.*;

public class Essential5Test {

    private static JsonNode SPEC;
    private static final Simply S = new Simply();

    private static JsonNode spec() throws Exception {
        if (SPEC == null) {
            File dir = new File(System.getProperty("user.dir")).getAbsoluteFile();
            File specFile = null;
            while (dir != null) {
                File candidate = new File(dir, "spec/stdlib/essential_5.json");
                if (candidate.isFile()) {
                    specFile = candidate;
                    break;
                }
                dir = dir.getParentFile();
            }
            assertNotNull(specFile, "essential_5.json not found");
            SPEC = new ObjectMapper().readTree(specFile);
        }
        return SPEC;
    }

    private static java.util.List<String> values(String pattern, String field) throws Exception {
        JsonNode arr = spec().get("patterns").get(pattern).get("fixtures").get(field);
        java.util.List<String> out = new java.util.ArrayList<>();
        for (JsonNode el : arr) out.add(el.asText());
        return out;
    }

    private static Pattern compile(com.strling.simply.Pattern p) {
        return Pattern.compile("^(?:" + S.build(p) + ")$");
    }

    private static void allMatch(Pattern re, java.util.List<String> values, String label) {
        for (String v : values) {
            assertTrue(re.matcher(v).matches(), label + " expected match: " + v);
        }
    }

    private static void noneMatch(Pattern re, java.util.List<String> values, String label) {
        for (String v : values) {
            assertFalse(re.matcher(v).matches(), label + " expected NO match: " + v);
        }
    }

    @Test public void emailValid() throws Exception {
        allMatch(compile(Essential.email()), values("email", "valid"), "email");
    }
    @Test public void emailInvalid() throws Exception {
        noneMatch(compile(Essential.email()), values("email", "invalid"), "email");
    }
    @Test public void urlValid() throws Exception {
        allMatch(compile(Essential.url()), values("url", "valid"), "url");
    }
    @Test public void urlInvalid() throws Exception {
        noneMatch(compile(Essential.url()), values("url", "invalid"), "url");
    }
    @Test public void uuidDefaultValid() throws Exception {
        allMatch(compile(Essential.uuid()), values("uuid", "valid_default"), "uuid");
    }
    @Test public void uuidDefaultInvalid() throws Exception {
        noneMatch(compile(Essential.uuid()), values("uuid", "invalid_default"), "uuid");
    }
    @Test public void uuid4Valid() throws Exception {
        allMatch(compile(Essential.uuid(4)), values("uuid", "valid_v4"), "uuid4");
    }
    @Test public void uuid4Invalid() throws Exception {
        noneMatch(compile(Essential.uuid(4)), values("uuid", "invalid_v4"), "uuid4");
    }
    @Test public void ipv4Valid() throws Exception {
        allMatch(compile(Essential.ip(4)), values("ip", "valid_v4"), "ipv4");
    }
    @Test public void ipv4Invalid() throws Exception {
        noneMatch(compile(Essential.ip(4)), values("ip", "invalid_v4"), "ipv4");
    }
    @Test public void ipv6Valid() throws Exception {
        allMatch(compile(Essential.ip(6)), values("ip", "valid_v6"), "ipv6");
    }
    @Test public void ipv6Invalid() throws Exception {
        noneMatch(compile(Essential.ip(6)), values("ip", "invalid_v6"), "ipv6");
    }
    @Test public void ipDefaultBoth() throws Exception {
        Pattern re = compile(Essential.ip());
        allMatch(re, values("ip", "valid_v4"), "ip");
        allMatch(re, values("ip", "valid_v6"), "ip");
    }
    @Test public void dateTimeValid() throws Exception {
        allMatch(compile(Essential.dateTime()), values("dateTime", "valid"), "dateTime");
    }
    @Test public void dateTimeInvalid() throws Exception {
        noneMatch(compile(Essential.dateTime()), values("dateTime", "invalid"), "dateTime");
    }
}
