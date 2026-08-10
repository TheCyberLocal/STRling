# Your First Contribution: The "Zip Code" Test

[← Back to Developer Hub](../index.md)

This tutorial guides you through the **Golden Path** contribution workflow. You will add a new conformance test case to STRling and verify it across multiple languages using the CLI.

---

## The Mission

We want to ensure STRling correctly handles a US Zip Code pattern: 5 digits, optionally followed by a hyphen and 4 more digits.

**Pattern:** `digit(5) + (("-" + digit(4)) | "")`

---

## Step 1: Create the Test Case

Conformance tests are defined in `.strl` files in `tests/conformance/cases/`.

1.  Create a new file `tests/conformance/cases/zip.strl`:

```strling
test "US Zip Code" {
    match "90210"
    match "12345-6789"
    reject "1234"
    reject "123456"
    reject "12345-123"
    reject "abcde"
}

pattern = digit(5) + (("-" + digit(4)) | "")
```

---

## Step 2: Generate Specifications

The TypeScript binding is the **transitional compatibility-fixture producer**.
The generated JSON records behavior that current bindings preserve; it is not a
normative specification or a “Golden Master.” A behavior change must first
identify its controlling specification, contract, or compatibility decision.

1.  Setup the TypeScript environment (if not already done):

    ```bash
    ./strling setup typescript
    ```

2.  Generate the specs:

    ```bash
    cd bindings/typescript
    npm run build:specs
    ```

    _Note: This command compiles the TypeScript binding and runs the fixture
    generator, creating a corresponding `zip.json` in `tests/spec/`. Review the
    generated value; generation itself does not approve behavior._

---

## Step 3: Verify Compatibility with Python

Now that the spec exists, we can verify that the Python binding correctly implements it.

1.  Setup the Python environment (if not already done):

    ```bash
    ./strling setup python
    ```

2.  Run the tests:

    ```bash
    ./strling test python
    ```

    You should see the new "US Zip Code" test case passing!

---

## Step 4: Verify with Other Languages

If you have other host-language toolchains installed (e.g., Rust or Go), verify
that they preserve the same transitional compatibility case.

```bash
# Optional: Verify Rust
./strling setup rust
./strling test rust
```

---

## Step 5: Commit

Once verified, commit your changes.

```bash
git add tests/conformance/cases/zip.strl tests/spec/zip.json
git commit -m "feat: add US Zip Code conformance test"
```

Congratulations! You've added a cross-binding compatibility case. Normative
Semantic STRling conformance cases follow the ratified specification process.
