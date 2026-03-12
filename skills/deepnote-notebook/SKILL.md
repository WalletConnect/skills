---
name: deepnote-notebook
description: Edit Deepnote .ipynb notebooks correctly by syncing the deepnote_source metadata field. Use when editing, creating, or modifying cells in Deepnote-exported Jupyter notebooks.
---

# Deepnote Notebook Editor

## Goal
Edit Deepnote `.ipynb` notebooks so that changes are visible when the file is re-imported into Deepnote.

## When to use
- Editing cells in a Deepnote-exported `.ipynb` file
- Adding new SQL or code cells to a Deepnote notebook
- Modifying queries or markdown in Deepnote notebooks

## When not to use
- Standard Jupyter notebooks (no `deepnote_source` in metadata)
- Notebooks created in JupyterLab, VS Code, or Colab

## The Problem

Deepnote notebooks look like standard `.ipynb` files but store a **duplicate** of each cell's content in `metadata.deepnote_source`. Deepnote reads from `deepnote_source` on import, NOT from the standard `source` field. If you only update `source` (which `NotebookEdit` does), Deepnote shows the **old** content.

## Cell Types

| `deepnote_cell_type` | ipynb `cell_type` | `deepnote_source` contains | `source` contains |
|---|---|---|---|
| `markdown` | `markdown` | Markdown text | Same markdown text |
| `text-cell-p` | `markdown` | Markdown text | Same markdown text |
| `code` | `code` | Python code | Same Python code |
| `sql` | `code` | **Raw SQL only** | Python wrapper (`_dntk.execute_sql(...)`) |

**SQL cells are critical** — `deepnote_source` has just the SQL, while `source` has the auto-generated Python wrapper.

### SQL Cell Metadata Fields

```json
{
  "deepnote_cell_type": "sql",
  "deepnote_variable_name": "df_result",
  "sql_integration_id": "uuid-of-database-integration",
  "deepnote_source": "SELECT * FROM table"
}
```

### SQL Cell Source Format

The Python wrapper in `source` follows this pattern:

```python
if '_dntk' in globals():
  _dntk.dataframe_utils.configure_dataframe_formatter('{}')
else:
  _deepnote_current_table_attrs = '{}'

df_result = _dntk.execute_sql(
  'SELECT * FROM table',
  'SQL_INTEGRATION_UUID',
  audit_sql_comment='',
  sql_cache_mode='cache_disabled',
  return_variable_type='dataframe'
)
df_result
```

Template variables use Jinja-style `{{VARIABLE|safe}}` syntax (double braces).

## Default Workflow

### 1) Read the notebook
Identify cell types and which cells need changes. Check for `deepnote_source` in metadata to confirm it is a Deepnote notebook.

### 2) Edit cells with NotebookEdit
Update `source` fields as usual.

### 3) Sync deepnote_source (mandatory)
Run a Python script to update `deepnote_source` for **all** modified/inserted cells:

```python
python3 << 'PYEOF'
import json

NOTEBOOK = '/path/to/notebook.ipynb'

with open(NOTEBOOK) as f:
    nb = json.load(f)

# For markdown/code cells — sync deepnote_source from source
cell = nb['cells'][CELL_INDEX]
cell['metadata']['deepnote_source'] = ''.join(cell['source'])

# For SQL cells — write the raw SQL directly (NOT the Python wrapper)
cell = nb['cells'][CELL_INDEX]
cell['metadata']['deepnote_source'] = """YOUR RAW SQL HERE"""

with open(NOTEBOOK, 'w') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
PYEOF
```

### 4) Adding new SQL cells
After inserting with `NotebookEdit`, set Deepnote metadata:

```python
cell = nb['cells'][INDEX]
cell['metadata']['deepnote_cell_type'] = 'sql'
cell['metadata']['deepnote_variable_name'] = 'df_result'
cell['metadata']['sql_integration_id'] = 'COPY_UUID_FROM_EXISTING_CELL'
cell['metadata']['deepnote_source'] = """SELECT ..."""
```

### 5) Verify
Grep for any stale content to confirm all references were updated.

## Validation checklist
- [ ] Every modified cell has `deepnote_source` updated
- [ ] SQL cells have raw SQL in `deepnote_source` (not the Python wrapper)
- [ ] New SQL cells have `deepnote_cell_type`, `deepnote_variable_name`, and `sql_integration_id`
- [ ] `grep` confirms no stale content remains in the file

## Examples

### Example 1: Update a SQL query
**Input:** User asks to change a SQL query in a Deepnote notebook.
**Output:**
1. `NotebookEdit` updates the `source` (Python wrapper with new SQL)
2. Python script sets `deepnote_source` to the new raw SQL
3. Grep verifies old query text is gone

### Example 2: Add a new chart section
**Input:** User asks to add a new SQL + chart cell pair.
**Output:**
1. `NotebookEdit` inserts a markdown cell, a code cell (SQL wrapper), and a code cell (chart)
2. Python script sets `deepnote_cell_type: sql`, copies `sql_integration_id` from an existing cell, sets `deepnote_variable_name`, and writes raw SQL to `deepnote_source`
3. Python script syncs `deepnote_source` for the markdown and chart cells from their `source`
