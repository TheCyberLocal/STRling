package strling

/**
 * Generated canonical standard-library identities for Simply 1.1.
 * These lexical helpers record registry identity; they do not validate semantics.
 */
object Essential {
    const val SOURCE_SHA256: String = "db3d1fc6ddd1b0ef83cb7bfb4a9bd84c8bcc547d5a6649a6747cc4b94fb4edff"
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
