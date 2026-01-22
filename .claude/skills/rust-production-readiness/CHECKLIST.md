# Rust Production Readiness Checklist

Detailed checklist for manual code review. Use alongside automated tooling.

## 1. Error Handling

### Critical
- [ ] No `unwrap()` on user input or external data
- [ ] No `unwrap()` on network responses
- [ ] No `expect()` with generic messages in production paths

### High
- [ ] `Result` types propagated with `?` or explicitly handled
- [ ] Error types carry context (not just `Box<dyn Error>` or `String`)
- [ ] Errors logged before being converted/wrapped

### Patterns to find
```bash
# Find unwrap/expect in non-test code
rg "\.unwrap\(\)" --type rust -g '!*test*' -g '!*tests*'
rg "\.expect\(" --type rust -g '!*test*' -g '!*tests*'
```

## 2. Panic Vectors

### Critical
- [ ] No `panic!()` in library code
- [ ] No `unreachable!()` that could actually be reached
- [ ] No `todo!()` or `unimplemented!()` in shipped code

### High
- [ ] Array/slice indexing bounds-checked or using `.get()`
- [ ] Integer arithmetic checked for overflow in release builds
- [ ] No `assert!()` for runtime conditions (use `Result` instead)

### Patterns to find
```bash
rg "panic!\(|todo!\(|unimplemented!\(|unreachable!\(" --type rust -g '!*test*'
rg "\[.*\]" --type rust  # Manual review for unchecked indexing
```

## 3. Unsafe Code

### Critical
- [ ] All `unsafe` blocks have `// SAFETY:` comments explaining invariants
- [ ] FFI boundaries validated (null checks, length checks)
- [ ] No undefined behavior (aliasing, uninitialized memory)

### High
- [ ] Unsafe code minimized and isolated
- [ ] Raw pointer lifetimes clearly bounded
- [ ] Transmutes justified and correct

### Patterns to find
```bash
rg "unsafe\s*\{" --type rust
rg "transmute" --type rust
```

## 4. Async & Concurrency

### Critical
- [ ] No `Mutex` held across `.await` points
- [ ] No blocking calls (std::fs, std::net) in async context
- [ ] Deadlock-free lock ordering

### High
- [ ] Timeouts on all network operations
- [ ] Cancellation handled gracefully
- [ ] No unbounded channel/queue growth

### Medium
- [ ] `Send + Sync` bounds explicit where needed
- [ ] Spawned tasks tracked or explicitly detached

### Patterns to find
```bash
rg "\.lock\(\)" --type rust -A 5  # Check if .await follows
rg "std::fs::|std::net::" --type rust  # Blocking in async?
```

## 5. Memory & Performance

### High
- [ ] No unbounded `Vec::push` in loops without pre-allocation
- [ ] No string concatenation in hot loops (use `String::with_capacity` or `format!`)
- [ ] Large structs passed by reference, not value
- [ ] No excessive `.clone()` on large types

### Medium
- [ ] `Box` used for large stack allocations
- [ ] Iterators preferred over collecting into intermediate `Vec`s
- [ ] `Cow` used where ownership is conditional

### Patterns to find
```bash
rg "\.clone\(\)" --type rust  # Review each for necessity
rg "\.collect::<Vec" --type rust  # Could this stay as iterator?
```

## 6. Dependencies

### Critical
- [ ] `cargo audit` shows no vulnerabilities
- [ ] No yanked crates in dependency tree
- [ ] Crypto dependencies from reputable sources

### High
- [ ] Dependency versions pinned or bounded appropriately
- [ ] No unnecessary dependencies
- [ ] Feature flags minimize compiled code

### Commands
```bash
cargo audit
cargo tree --duplicates  # Check for version conflicts
cargo deny check  # If cargo-deny configured
```

## 7. API & Documentation

### High
- [ ] Public API has doc comments
- [ ] Error conditions documented
- [ ] Panics documented (if any exist intentionally)
- [ ] Examples compile (`cargo test --doc`)

### Medium
- [ ] `#[must_use]` on functions returning important values
- [ ] `#[non_exhaustive]` on public enums that may grow
- [ ] Breaking changes noted in changelog

## 8. Testing

### High
- [ ] Unit tests for core logic
- [ ] Integration tests for public API
- [ ] Error paths tested, not just happy path

### Medium
- [ ] Edge cases covered (empty input, max values, unicode)
- [ ] Async tests use appropriate runtime
- [ ] Mocks/fakes for external services

### Commands
```bash
cargo test --all-features
cargo tarpaulin  # Coverage if available
```

## 9. Configuration & Environment

### Critical
- [ ] No hardcoded secrets or API keys
- [ ] Secrets loaded from environment or secure storage
- [ ] No `println!` debug output in production code

### High
- [ ] Configuration validated at startup
- [ ] Sensible defaults for optional config
- [ ] Feature flags documented

### Patterns to find
```bash
rg "println!\(|dbg!\(" --type rust -g '!*test*'
rg "HARDCODED|TODO|FIXME|XXX" --type rust
```

## 10. Build & Release

### High
- [ ] `cargo build --release` succeeds
- [ ] No compiler warnings with `-D warnings`
- [ ] MSRV (minimum supported Rust version) documented and tested
- [ ] Cross-compilation targets build (if applicable)

### Commands
```bash
cargo build --release --all-features
cargo clippy --all-targets --all-features -- -D warnings
```
