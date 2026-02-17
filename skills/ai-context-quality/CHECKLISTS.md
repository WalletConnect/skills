# AI Context Quality Checklists

Detailed criteria used by each analysis subagent. Referenced from [SKILL.md](SKILL.md).

## Reference Validity Checklist

Check every reference in context files against the actual codebase:

### File and Directory References
- [ ] File paths resolve to existing files (`src/utils/auth.ts` exists)
- [ ] Directory paths resolve to existing directories (`src/components/` exists)
- [ ] Glob patterns match at least one file (`**/*.test.ts` returns results)
- [ ] Relative paths are correct from the context file's location

### Code References
- [ ] Function/method names exist in the codebase (`handlePayment` is defined somewhere)
- [ ] Class/type/interface names exist (`UserService`, `PaymentState`)
- [ ] Variable and constant names exist (`API_BASE_URL`, `MAX_RETRIES`)
- [ ] Module/package imports are valid

### Dependency References
- [ ] Package names match entries in dependency manifests
- [ ] Referenced CLI tools are available (`npm`, `cargo`, `pnpm`)
- [ ] Referenced scripts exist in `package.json` scripts or equivalent

### External References
- [ ] URLs are not obviously broken (check format, not availability)
- [ ] Referenced third-party services/APIs match actual integrations in code

### Scoring Guide
- **100**: All references valid
- **80-99**: Minor stale references (renamed files, moved directories)
- **60-79**: Several broken references but core instructions still work
- **40-59**: Major references broken, agent will get confused
- **<40**: Most references are stale, context actively misleads

---

## Coverage Checklist

Verify that context files document the key areas of the codebase:

### Essential (heavily weighted)
- [ ] **Tech stack**: Languages, frameworks, and major libraries identified
- [ ] **Architecture**: High-level structure described (monorepo? microservices? monolith?)
- [ ] **Directory structure**: Key directories and their purpose explained
- [ ] **Build and run**: How to build, run, and develop locally

### Important
- [ ] **Code conventions**: Naming patterns, file organization, import style
- [ ] **Testing approach**: Test framework, patterns, how to run tests
- [ ] **Key abstractions**: Core patterns, base classes, shared utilities documented
- [ ] **Error handling**: How errors are handled, logged, and reported
- [ ] **State management**: State patterns (if frontend: Redux/Context/XState; if backend: DB/cache)

### Helpful
- [ ] **Deployment**: How code gets deployed, environments, CI/CD
- [ ] **API patterns**: REST/GraphQL conventions, auth patterns
- [ ] **Environment setup**: Required env vars, secrets, config files
- [ ] **Dependencies**: Key dependencies and why they're used
- [ ] **Anti-patterns**: What to avoid and why

### Scoring Guide
- **100**: All essential + important areas covered with relevant detail
- **80-99**: All essential covered, most important covered
- **60-79**: Essential areas covered but missing important context
- **40-59**: Some essential areas missing
- **<40**: Most areas undocumented

---

## Clarity Checklist

Evaluate how well instructions communicate to an AI agent:

### Specificity
- [ ] Instructions are imperative and concrete, not vague
  - Bad: "Handle errors properly"
  - Good: "Use `Result<T, AppError>` for all fallible operations. Propagate with `?`. Log at the boundary."
- [ ] Code patterns include examples (show, don't just tell)
- [ ] File paths are specific, not hand-wavy ("the config file" vs "`src/config/app.ts`")
- [ ] Numeric thresholds are explicit when relevant ("80% coverage" vs "good coverage")

### Structure
- [ ] Sections are logically organized and easy to scan
- [ ] Headers clearly describe section content
- [ ] Lists are used for multiple items (not buried in paragraphs)
- [ ] Length is appropriate:
  - Under 20 lines: likely too sparse to be useful
  - 20-200 lines: typically appropriate for root context files
  - 200-500 lines: acceptable for detailed skill files
  - Over 500 lines: should be split into reference files

### Consistency
- [ ] Same concept uses same term throughout (not "component" in one place, "widget" in another)
- [ ] Style is consistent across all context files (tone, formatting, depth)
- [ ] No contradictory instructions across files

### Actionability
- [ ] Agent can follow instructions without guessing intent
- [ ] Decision points have clear criteria (when to use A vs B)
- [ ] Anti-patterns are called out with reasons (not just "don't do X")
- [ ] Examples show both correct and incorrect approaches where helpful

### Scoring Guide
- **100**: Crystal clear, specific, well-structured, consistent
- **80-99**: Clear with minor vagueness or formatting issues
- **60-79**: Understandable but frequently vague or poorly structured
- **40-59**: Often unclear, agent must guess intent
- **<40**: Instructions are too vague to be useful
