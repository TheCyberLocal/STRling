package strling

import kotlinx.serialization.json.*
import strling.core.Compiler
import strling.emitters.Pcre2Emitter
import java.io.File
import java.util.regex.Pattern as JPattern
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class Essential5Test {

    private val spec: JsonObject by lazy {
        var dir: File? = File(".").absoluteFile
        var found: File? = null
        while (dir != null) {
            val candidate = File(dir, "spec/stdlib/essential_5.json")
            if (candidate.isFile) { found = candidate; break }
            dir = dir.parentFile
        }
        requireNotNull(found) { "essential_5.json not found" }
        Json.parseToJsonElement(found.readText()).jsonObject
    }

    private fun values(pattern: String, field: String): List<String> {
        val arr = spec["patterns"]!!.jsonObject[pattern]!!.jsonObject["fixtures"]!!.jsonObject[field]!!.jsonArray
        return arr.map { it.jsonPrimitive.content }
    }

    private fun compile(p: Pattern): JPattern {
        val ir = Compiler.compile(p.node)
        val regex = Pcre2Emitter.emit(ir, null)
        return JPattern.compile("^(?:" + regex + ")$")
    }

    private fun allMatch(re: JPattern, vals: List<String>, label: String) {
        for (v in vals) assertTrue(re.matcher(v).matches(), "$label expected match: $v")
    }
    private fun noneMatch(re: JPattern, vals: List<String>, label: String) {
        for (v in vals) assertFalse(re.matcher(v).matches(), "$label expected NO match: $v")
    }

    @Test fun emailValid() = allMatch(compile(Essential.email()), values("email", "valid"), "email")
    @Test fun emailInvalid() = noneMatch(compile(Essential.email()), values("email", "invalid"), "email")
    @Test fun urlValid() = allMatch(compile(Essential.url()), values("url", "valid"), "url")
    @Test fun urlInvalid() = noneMatch(compile(Essential.url()), values("url", "invalid"), "url")
    @Test fun uuidDefaultValid() = allMatch(compile(Essential.uuid()), values("uuid", "valid_default"), "uuid")
    @Test fun uuidDefaultInvalid() = noneMatch(compile(Essential.uuid()), values("uuid", "invalid_default"), "uuid")
    @Test fun uuid4Valid() = allMatch(compile(Essential.uuid(4)), values("uuid", "valid_v4"), "uuid4")
    @Test fun uuid4Invalid() = noneMatch(compile(Essential.uuid(4)), values("uuid", "invalid_v4"), "uuid4")
    @Test fun ipv4Valid() = allMatch(compile(Essential.ip(4)), values("ip", "valid_v4"), "ipv4")
    @Test fun ipv4Invalid() = noneMatch(compile(Essential.ip(4)), values("ip", "invalid_v4"), "ipv4")
    @Test fun ipv6Valid() = allMatch(compile(Essential.ip(6)), values("ip", "valid_v6"), "ipv6")
    @Test fun ipv6Invalid() = noneMatch(compile(Essential.ip(6)), values("ip", "invalid_v6"), "ipv6")
    @Test fun ipDefaultBoth() {
        val re = compile(Essential.ip())
        allMatch(re, values("ip", "valid_v4"), "ip")
        allMatch(re, values("ip", "valid_v6"), "ip")
    }
    @Test fun dateTimeValid() = allMatch(compile(Essential.dateTime()), values("dateTime", "valid"), "dateTime")
    @Test fun dateTimeInvalid() = noneMatch(compile(Essential.dateTime()), values("dateTime", "invalid"), "dateTime")
}
