package strling

/**
 * Generated canonical standard-library identities for Simply 1.1.
 * These lexical helpers record registry identity; they do not validate semantics.
 */
object Essential {
    const val SOURCE_SHA256: String = "36779a57c8016a0ff4a1ba00e9c6cb198246bf8e170edb1e0d627c0ed91f19a0"
    const val REGISTRY_VERSION: String = "1.0.0"
    val HELPER_IDS: List<String> = listOf(
        "stdlib.date_time",
        "stdlib.email",
        "stdlib.ip",
        "stdlib.url",
        "stdlib.uuid",
    )

    fun dateTime(): Pattern =
        Pattern.stdlibHelper("stdlib.date_time", emptyMap<String, Any?>())

    fun email(): Pattern =
        Pattern.stdlibHelper("stdlib.email", emptyMap<String, Any?>())

    fun ip(version: Int? = null): Pattern =
        Pattern.stdlibHelper("stdlib.ip", mapOf("version" to version))

    fun url(): Pattern =
        Pattern.stdlibHelper("stdlib.url", emptyMap<String, Any?>())

    fun uuid(version: Int? = null): Pattern =
        Pattern.stdlibHelper("stdlib.uuid", mapOf("version" to version))

}
