### Document Tools (DX-76)

| I want to... | Use |
|--------------|-----|
| View document structure | `{% if syntax == "mcp" %}invar_doc_toc(file="<file>"){% else %}invar doc toc <file> [--format text]{% endif %}` |
| Read specific section | `{% if syntax == "mcp" %}invar_doc_read(file="<file>", section="<section>"){% else %}invar doc read <file> <section>{% endif %}` |
| Search sections by title | `{% if syntax == "mcp" %}invar_doc_find(file="<file>", pattern="<pattern>"){% else %}invar doc find <pattern> <files...>{% endif %}` |
| Replace section content | `{% if syntax == "mcp" %}invar_doc_replace(file="<file>", section="<section>"){% else %}invar doc replace <file> <section>{% endif %}` |
| Insert new section | `{% if syntax == "mcp" %}invar_doc_insert(file="<file>", anchor="<anchor>"){% else %}invar doc insert <file> <anchor>{% endif %}` |
| Delete section | `{% if syntax == "mcp" %}invar_doc_delete(file="<file>", section="<section>"){% else %}invar doc delete <file> <section>{% endif %}` |

**Section addressing:** slug path (`requirements/auth`), fuzzy (`auth`), index (`#0/#1`), line (`@48`)

## Tool Selection

### Calling Methods (Priority Order)

Invar tools can be called in 3 ways. **Try in order:**

1. **MCP tools** (Claude Code with MCP enabled)
   - Direct function calls: `invar_guard()`, `invar_sig()`, etc.
   - No Bash wrapper needed

2. **CLI command** (if `invar` installed in PATH)
   - Via Bash: `invar guard`, `invar sig`, etc.
   - Install: `pip install invar-tools`

3. **uvx fallback** (always available, no install needed)
   - Via Bash: `uvx invar-tools guard`, `uvx invar-tools sig`, etc.

---

### Parameter Reference

**guard** - Verify code quality
```{% if syntax == "mcp" %}python
# MCP
invar_guard()                    # Check changed files (default)
invar_guard(changed=False)       # Check all files{% else %}bash
# CLI
invar guard                      # Check changed files (default)
invar guard --all                # Check all files{% endif %}
```

**sig** - Show function signatures and contracts
```{% if syntax == "mcp" %}python
# MCP
invar_sig(target="src/foo.py"){% else %}bash
# CLI
invar sig src/foo.py
invar sig src/foo.py::function_name{% endif %}
```

**map** - Find entry points
```{% if syntax == "mcp" %}python
# MCP
invar_map(path=".", top=10){% else %}bash
# CLI
invar map [path] --top 10{% endif %}
```

**refs** - Find all references to a symbol
```{% if syntax == "mcp" %}python
# MCP
invar_refs(target="src/foo.py::MyClass"){% else %}bash
# CLI
invar refs src/foo.py::MyClass{% endif %}
```

**doc*** - Document tools
```{% if syntax == "mcp" %}python
# MCP
invar_doc_toc(file="docs/spec.md")
invar_doc_read(file="docs/spec.md", section="intro"){% else %}bash
# CLI
invar doc toc docs/spec.md
invar doc read docs/spec.md intro{% endif %}
```

---

### Quick Examples

```{% if syntax == "mcp" %}python
# Verify after changes (all three methods identical)
invar_guard()                        # MCP
bash("invar guard")                  # CLI
bash("uvx invar-tools guard")        # uvx

# Full project check
invar_guard(changed=False)           # MCP
bash("invar guard --all")            # CLI

# See function contracts
invar_sig(target="src/core/parser.py")
bash("invar sig src/core/parser.py"){% else %}bash
# Verify after changes (all three methods identical)
invar guard                          # CLI
uvx invar-tools guard                # uvx

# Full project check
invar guard --all                    # CLI
uvx invar-tools guard --all          # uvx

# See function contracts
invar sig src/core/parser.py
uvx invar-tools sig src/core/parser.py{% endif %}
```

**Note**: All three methods now have identical default behavior.
