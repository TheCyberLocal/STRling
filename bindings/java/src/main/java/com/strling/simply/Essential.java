package com.strling.simply;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Generated canonical standard-library identities for Simply 1.1.
 * These lexical helpers record registry identity; they do not validate semantics.
 */
public final class Essential {
    public static final String SOURCE_SHA256 = "c7b7bbf7ed8ebc947402c172ae4f933ee1bccc91f39a020df239fb4678fbd5df";
    public static final String REGISTRY_VERSION = "1.0.0";
    public static final List<String> HELPER_IDS = Collections.unmodifiableList(
            java.util.Arrays.asList(
                    "stdlib.date_time",
                    "stdlib.email",
                    "stdlib.ip",
                    "stdlib.url",
                    "stdlib.uuid"
            ));

    private Essential() {}

    public static Pattern dateTime() {
        return Pattern.stdlibHelper("stdlib.date_time", Collections.emptyMap());
    }

    public static Pattern email() {
        return Pattern.stdlibHelper("stdlib.email", Collections.emptyMap());
    }

    public static Pattern ip() {
        return ip(null);
    }

    public static Pattern ip(Integer version) {
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("version", version);
        return Pattern.stdlibHelper("stdlib.ip", parameters);
    }

    public static Pattern url() {
        return Pattern.stdlibHelper("stdlib.url", Collections.emptyMap());
    }

    public static Pattern uuid() {
        return uuid(null);
    }

    public static Pattern uuid(Integer version) {
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("version", version);
        return Pattern.stdlibHelper("stdlib.uuid", parameters);
    }

}
