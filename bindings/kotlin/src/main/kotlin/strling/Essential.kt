package strling

/**
 * Generated canonical standard-library identities for Simply 1.1.
 * These lexical helpers record registry identity; they do not validate semantics.
 */
object Essential {
    const val SOURCE_SHA256: String = "94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d"
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
