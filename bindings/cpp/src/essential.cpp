#include "strling/essential.hpp"

// Canonical lexical-shape helpers delegate by registry identity and do not
// claim semantic validation.

namespace strling::essential {

simply::pattern email()
{
    return simply::stdlib_helper("stdlib.email");
}

simply::pattern url()
{
    return simply::stdlib_helper("stdlib.url");
}

simply::pattern uuid()
{
    return simply::stdlib_helper("stdlib.uuid", SL_STDLIB_NULL_VERSION);
}

simply::pattern uuid_v4()
{
    return simply::stdlib_helper("stdlib.uuid", 4);
}

simply::pattern ip_v4()
{
    return simply::stdlib_helper("stdlib.ip", 4);
}

simply::pattern ip_v6()
{
    return simply::stdlib_helper("stdlib.ip", 6);
}

simply::pattern ip_any()
{
    return simply::stdlib_helper("stdlib.ip", SL_STDLIB_NULL_VERSION);
}

simply::pattern date_time()
{
    return simply::stdlib_helper("stdlib.date_time");
}

} // namespace strling::essential
