---
name: supply-chain-security
description: Detects supply-chain attack patterns in code changes — invisible Unicode obfuscation (Glassworm), malicious install hooks, eval-based payload decoders, and lockfile anomalies. Use during code review, PR analysis, or when auditing dependencies.
---

# Supply Chain Security Review

When reviewing code changes, pull requests, or dependencies, check for these supply-chain attack indicators. This skill is informed by the **Glassworm** campaign (March 2026), which compromised 151+ GitHub repositories, npm packages, and VS Code extensions using invisible Unicode payloads.

## Invisible Unicode Obfuscation

The Glassworm campaign encodes malicious payloads inside what looks like empty strings or blank lines using Private Use Area (PUA) Unicode characters that are invisible in every major editor, terminal, and GitHub's code review UI.

### Target character ranges

- **Variation Selectors**: U+FE00–U+FE0F (UTF-8 bytes: `EF B8 80` – `EF B8 8F`)
- **Variation Selectors Supplement**: U+E0100–U+E01EF (UTF-8 bytes: `F3 A0 84 80` – `F3 A0 87 AF`)
- **Zero-width characters**: U+200B (zero-width space), U+200C (ZWNJ), U+200D (ZWJ), U+2060 (word joiner), U+FEFF (BOM when mid-file)

### The decoder pattern

The attacker hides bytes in invisible characters, then decodes them at runtime:

```javascript
// This is what the Glassworm decoder looks like — FLAG THIS PATTERN
const s = v => [...v].map(w => (
  w = w.codePointAt(0),
  w >= 0xFE00 && w <= 0xFE0F ? w - 0xFE00 :
  w >= 0xE0100 && w <= 0xE01EF ? w - 0xE0100 + 16 : null
)).filter(n => n !== null);
eval(Buffer.from(s(``)).toString('utf-8'));
// The backticks above contain thousands of invisible characters
```

### Detection commands

When you suspect hidden content, run these checks:

```bash
# Scan for PUA variation selectors via hex dump
xxd -p <file> | tr -d '\n' | grep -iE 'efb88[0-9a-f]'

# Scan an entire directory
find . -type f \( -name '*.js' -o -name '*.ts' -o -name '*.json' \) \
  ! -path '*/node_modules/*' -exec sh -c \
  'xxd -p "$1" | tr -d "\n" | grep -qiE "efb88[0-9a-f]" && echo "FOUND: $1"' _ {} \;

# Check for zero-width characters
grep -rPn '[\x{200B}\x{200C}\x{200D}\x{2060}]' . --include='*.js' --include='*.ts'

# Byte-count anomaly: find lines with many bytes but few visible chars
awk '{ bytes=length($0); gsub(/[^[:print:]]/, ""); visible=length($0); if (bytes > 500 && visible < 20) print FILENAME":"NR": "bytes" bytes, "visible" visible chars" }' <file>
```

## Malicious Code Patterns

Flag these patterns in any PR or dependency change:

1. **`eval()` with `Buffer.from()`** — the standard Glassworm decoder
2. **`codePointAt()` with hex ranges `0xFE00`–`0xFE0F` or `0xE0100`** — Unicode extraction
3. **Template literals passed to `eval()`** — payload delivery
4. **`new Function()` with encoded strings** — alternative to eval
5. **Unexpected `preinstall` / `postinstall` / `preuninstall`** hooks in `package.json`
6. **Lockfile changes without corresponding dependency additions** in `package.json`

## PR Review Red Flags

- **Trusted contributor** submitting changes to lockfiles or `package.json` hooks without a clear reason
- **"Cleanup" or "docs" PRs** that touch script fields, build configs, or CI files
- **Empty-looking lines** in diffs that could contain invisible characters — check file size or byte count
- **Force-pushed commits** that rewrite history on the default branch
- **Commits where author/timestamp looks preserved** but content has changed (no PR trail)
- **AI-generated cover changes** — small, stylistically consistent refactors wrapping malicious injections

## Byte-Count Cross-Check

When reviewing diffs, if you have bash tool access, always cross-check suspicious files:

```bash
# Compare file byte size against visible content
wc -c <file>           # total bytes
wc -m <file>           # character count
cat <file> | tr -cd '[:print:]\n' | wc -c  # printable chars only
```

If the byte count significantly exceeds the printable character count, the file likely contains hidden content.