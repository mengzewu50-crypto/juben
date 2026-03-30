---
name: managing-notebooklm
description: Manages NotebookLM notebooks, sources, and notes via MCP. Use when the user wants to research, query existing documents, or generate AI artifacts like podcasts and study guides from their Google NotebookLM account.
---

# Managing NotebookLM

## When to use this skill

- Researching topics using web or Google Drive sources.
- Querying information from existing notebooks or across multiple notebooks.
- Organizing information by creating, renaming, or deleting notebooks and notes.
- Generating and downloading "Studio" artifacts like Audio Overviews (podcasts), quizzes, and slide decks.
- Managing collaborators and public sharing for notebooks.

## Workflow

The agent should follow this state-tracking checklist:

- [ ] **Verify Authentication**: Run `server_info` or `refresh_auth` if token issues occur.
- [ ] **Identify Context**: Use `notebook_list` to find relevant notebooks or `tag` to select by category.
- [ ] **Gather Information**: Use `notebook_get` or `source_list_drive` to understand existing content.
- [ ] **Process/Expand**: Use `source_add` or `research_start` to bring in new data.
- [ ] **Synthesize**: Use `notebook_query` or `studio_create` to generate final outputs.
- [ ] **Export/Cleanup**: Use `export_artifact` or `download_artifact` to save results.

## Instructions

### 1. Authentication and Setup
- **Initial check**: Always run `server_info` to check if the server is up and if updates are available.
- **Login Issues**: If tools return auth errors, advise the user to run `nlm login` in the terminal. Do NOT ask for cookies unless the CLI method fails. Use `refresh_auth` after a CLI login.

### 2. Research and Source Ingestion (Automated Import)
- **Starting Research**: Use `research_start`. This initiates the search but does NOT add content to the notebook yet.
- **Automated Import Cycle**:
  - **Wait & Poll**: Deep research typically takes ~5 minutes. After initiation, call `research_status` with `max_wait=600` (10 minutes) and `poll_interval=60`.
  - **Import**: Once `status` is "completed", IMMEDIATELY call `research_import`.
  - **Constraint**: Do NOT ask the user for permission to import if they have already provided the research query. Proceed automatically to the import step once data is ready.

### 3. Querying & AI Interaction
- **Specific Notebook**: Use `notebook_query` for questions about a single notebook.
- **Cross-Notebook**: Use `cross_notebook_query` or `batch(action="query")` when the answer might span multiple projects.
- **Configuration**: Use `chat_configure` to adjust the AI's persona (e.g., "learning_guide") or response length.

### 4. Studio & Artifact Generation
- **Creation**: Use `studio_create`. This requires a `confirm=True` parameter from the user often, but the tool accepts it as a param. 
- **Monitoring**: Generation is asynchronous. Call `studio_status` to get the URL once `status` is "completed".
- **Downloading**: Always use `download_artifact` with a clear `output_path`. Match the `artifact_type` exactly (e.g., `audio`, `quiz`).

### 5. Organization
- **Tagging**: Use `tag(action="add")` to categorize notebooks. This allows for easier retrieval later using `tag(action="select")`.
- **Note Management**: Use the unified `note` tool for all CRUD operations on user notes.

## Resources

- [NotebookLM Official Site](https://notebooklm.google.com/)
- [MCP Server Documentation](file:///C:/Users/14792/AppData/Roaming/npm/node_modules/@antigravity/notebooklm-mcp/README.md) (Check if local docs exist)
