## 🐛 Issue Description

## 🌍 Context (Crucial)

-   **Affected Binding:** [e.g., Python, Rust, TypeScript, C#]
-   **STRling Version:** [e.g., v3.0.0]
-   **Host OS:** [e.g., Ubuntu 22.04, Windows 11, macOS 14]
-   **Runtime Version:** [e.g., Python 3.10, Node 22, .NET 9]

---

## 🕵️ Architecture Triage

**Is this a Core Logic error?**

-   [ ] **Yes:** The issue is in how the regex is parsed or optimized (likely affects ALL languages).
-   [ ] **No:** The issue is specific to this binding (e.g., installation, type hints, crash in the wrapper).
-   [ ] **Unsure**

**Is this a Spec Compliance error?**

-   [ ] **Yes:** The binding behavior contradicts the Shared JSON Specs in `tests/spec/`.
-   [ ] **No:** This seems to be an edge case not covered by existing specs.

---

## 💥 Reproduction Steps

1. Install STRling via...
2. Run the following code:

```code_lang
// Insert code here
// e.g. simply.literal("foo").digit()
```

3.  See error...

### Expected Behavior

### Actual Behavior

---

## 🎓 Instructional Error Check

-   **Did the error message explain _why_ the pattern failed?**
-   [ ] Yes (The error was helpful but the behavior is wrong)
-   [ ] No (The error was cryptic/stack trace only)

## 🛡️ Security Check

-   [ ] I verify that this is **NOT** a security vulnerability (ReDoS or Compiler Panic).

_If it IS a security vulnerability, please report it via GitHub Security Advisories instead._
