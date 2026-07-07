import io
import os
import zipfile
import logging
import asyncio
import json
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from backend.app.core.database import Database

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[ChatMessage] = []

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve job metadata and current analysis status."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Remove large document content from status response to keep payload small
    job_info = dict(job)
    job_info.pop("readme_content", None)
    job_info.pop("devdoc_content", None)
    
    return job_info

@router.get("/{job_id}/readme")
async def get_job_readme(job_id: str):
    """Fetch the generated README.md content."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
        
    readme_content = job.get("readme_content", "")
    return PlainTextResponse(readme_content)

@router.get("/{job_id}/devdoc")
async def get_job_devdoc(job_id: str):
    """Fetch the generated DEVELOPER.md content."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
        
    devdoc_content = job.get("devdoc_content", "")
    return PlainTextResponse(devdoc_content)

@router.get("/{job_id}/download")
async def download_job_docs(job_id: str):
    """Download a ZIP archive containing both generated documentation files."""
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
        
    readme_content = job.get("readme_content", "")
    devdoc_content = job.get("devdoc_content", "")
    project_name = job.get("project_name", "project")
    
    # Create in-memory zip archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("README.md", readme_content)
        zip_file.writestr("DEVELOPER.md", devdoc_content)
        
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f"attachment; filename={project_name}_docs.zip"
        }
    )

@router.post("/{job_id}/chat")
async def chat_codebase(job_id: str, request: ChatRequest):
    """
    RAG-style chatbot to answer questions about the analyzed codebase with context memory and streaming response.
    """
    jobs_col = Database.get_collection("jobs")
    job = jobs_col.find_one({"_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail="Job is not completed yet.")
        
    query = request.question.strip().lower()
    project_model = job.get("project_model", {})
    if not project_model:
        # Fallback to general info if project model wasn't stored (legacy job)
        project_model = {
            "name": job.get("project_name", "Project"),
            "files": [],
            "dependencies": job.get("dependencies", []),
            "detected_frameworks": job.get("frameworks", [])
        }
        
    files = project_model.get("files", [])
    dependencies = project_model.get("dependencies", [])
    frameworks = project_model.get("detected_frameworks", [])
    
    # ── Context Memory Tracking ──────────────────────────────────────────────
    context_file = None
    context_class = None
    context_func = None
    
    for msg in reversed(request.history):
        if msg.role == "assistant":
            import re
            file_match = re.search(r'Overview:\s*\[([\w/\\.-]+)\]', msg.content)
            if file_match:
                context_file = file_match.group(1)
                
            class_match = re.search(r'Class:\s*`(\w+)`', msg.content)
            if class_match:
                context_class = class_match.group(1)
                
            func_match = re.search(r'Function:\s*`(\w+)`', msg.content)
            if func_match:
                context_func = func_match.group(1)
                
            if context_file or context_class or context_func:
                break
                
    # ── Rule-based router ─────────────────────────────────────────────────────
    answer = None
    sources = []
    
    is_followup = any(w in query for w in ["it", "its", "this", "describe", "explain", "detail", "more", "functions", "methods", "classes", "loc", "lines", "imports", "code", "show", "list"])
    
    if is_followup:
        # Class follow-up
        if context_class and any(w in query for w in ["method", "methods", "function", "functions"]):
            for f in files:
                for cls in f.get("classes", []):
                    if cls["name"].lower() == context_class.lower():
                        methods_str = ", ".join([f"`{m['name']}`" for m in cls.get("methods", [])]) if cls.get("methods") else "none"
                        answer = f"The class `{cls['name']}` has the following methods:\n\n{methods_str}"
                        sources = [f["path"]]
                        break
                if answer:
                    break
                    
        # File follow-up
        if not answer and context_file:
            for f in files:
                if f["path"].lower() == context_file.lower() or os.path.basename(f["path"]).lower() == context_file.lower():
                    if any(w in query for w in ["function", "functions", "method", "methods"]):
                        funcs_str = "\n".join([f"- `{fn['name']}` (line {fn['line_number']})" for fn in f.get("functions", [])]) if f.get("functions") else "No global functions defined."
                        answer = f"### ⚙️ Functions in [{f['path']}]\nHere are the functions defined in this file:\n\n{funcs_str}"
                        sources = [f["path"]]
                        break
                    elif any(w in query for w in ["class", "classes"]):
                        classes_str = "\n".join([f"- `{c['name']}` (line {c['line_number']})" for c in f.get("classes", [])]) if f.get("classes") else "No classes defined."
                        answer = f"### 🏛️ Classes in [{f['path']}]\nHere are the classes defined in this file:\n\n{classes_str}"
                        sources = [f["path"]]
                        break
                    elif any(w in query for w in ["import", "imports"]):
                        imports_str = "\n".join([f"- `{imp}`" for imp in f.get("imports", [])]) if f.get("imports") else "No imports."
                        answer = f"### 📦 Imports in [{f['path']}]\nThis file imports the following modules:\n\n{imports_str}"
                        sources = [f["path"]]
                        break
                    elif any(w in query for w in ["loc", "line", "lines"]):
                        answer = f"The file [{f['path']}] has **{f['loc']}** lines of code (LOC)."
                        sources = [f["path"]]
                        break
                        
    # Standard router rules (if not follow-up, or follow-up did not match anything)
    if not answer:
        # 1. Dependency Queries
        dep_keywords = ["dependency", "dependencies", "package", "packages", "library", "libraries", "pip", "npm", "requirements"]
        if any(k in query for k in dep_keywords):
            if not dependencies:
                answer = "No dependencies or package lists were detected in this codebase."
            else:
                dep_list_str = "\n".join([f"- **{d['name']}** (version: `{d.get('version') or '*'}`) - via *{d.get('source')}*" for d in dependencies])
                answer = f"### 📦 Detected Dependencies ({len(dependencies)})\nHere are the third-party libraries and packages used in this project:\n\n{dep_list_str}"
                
        # 1.5. File/Files Overview Queries
        elif any(k in query for k in ["file", "files", "overview", "structure", "tree", "catalog", "directory"]):
            if not files:
                answer = "No files were detected in this codebase."
            else:
                file_list_str = "\n".join([f"- **{f['path']}** ({f['language']}, {f['loc']} LOC)" for f in files[:25]])
                if len(files) > 25:
                    file_list_str += f"\n- *and {len(files) - 25} more files...*"
                answer = f"### 📁 Codebase Files Overview ({len(files)} files)\nHere are the files detected in this codebase:\n\n{file_list_str}"
                
        # 2. API Routes / Endpoints Queries
        elif any(k in query for k in ["route", "routes", "endpoint", "endpoints", "api", "url", "urls", "path", "http"]):
            routes = []
            for f in files:
                for fn in f.get("functions", []):
                    for dec in fn.get("decorators", []):
                        import re
                        m = re.match(r'(\w+)\.(get|post|put|patch|delete|route)\(', dec)
                        if m:
                            method = m.group(2).upper()
                            if method == "ROUTE":
                                method = "GET"
                            path_match = re.search(r'[\'"]([/\w{}<>:_-]+)[\'"]', dec)
                            path = path_match.group(1) if path_match else "/unknown"
                            routes.append({
                                "method": method,
                                "path": path,
                                "handler": fn["name"],
                                "file": f["path"],
                                "desc": fn["docstring"].split(".")[0] if fn.get("docstring") else ""
                            })
            if not routes:
                answer = "No HTTP API routes or endpoint decorators (e.g. `@app.get`, `@router.post`) were found in this codebase."
            else:
                routes_str = "\n".join([f"- **{r['method']}** `{r['path']}` -> mapped to `{r['handler']}` in [{r['file']}] (Description: *{r['desc'] or 'none'}*)" for r in routes])
                answer = f"### 🔌 API Routes & Endpoints ({len(routes)})\nI found the following API request handlers in the codebase:\n\n{routes_str}"
                sources = list(set([r["file"] for r in routes[:3]]))
                
        # 3. Stack / Frameworks Detections
        elif any(k in query for k in ["framework", "frameworks", "stack", "technology", "technologies", "django", "flask", "fastapi", "react", "vue"]):
            if not frameworks:
                answer = "This appears to be a standard utility codebase. No major web frameworks (like FastAPI, Django, Flask, or React) were identified."
            else:
                fw_list_str = "\n".join([f"- **{fw}**" for fw in frameworks])
                answer = f"### 🛠️ Technology Stack\nThis codebase relies on the following frameworks/technologies:\n\n{fw_list_str}"
                
        # 3.1. Entry Points / Running
        elif any(k in query for k in ["entry", "run", "start", "main", "launch", "execute", "executable"]):
            entry_points = project_model.get("entry_points", [])
            found_entries = []
            for f in files:
                fname = os.path.basename(f["path"]).lower()
                if fname in ["main.py", "app.py", "index.js", "server.js", "manage.py", "wsgi.py", "asgi.py"]:
                    found_entries.append(f["path"])
            
            all_entries = list(set(entry_points + found_entries))
            if not all_entries:
                answer = "I couldn't identify any standard project entry points. Look for files with main function decorators or entry-level execution blocks."
            else:
                entries_str = "\n".join([f"- **[{entry}]**" for entry in all_entries])
                answer = f"### 🚀 Project Entry Points\nTo run or initialize this project, you should execute or target these entry-level files:\n\n{entries_str}"
                sources = all_entries[:3]

        # 3.2. Project Size & LOC Metrics
        elif any(k in query for k in ["loc", "lines", "size", "metrics", "count", "how big", "statistics"]):
            lang_breakdown = {}
            total_loc = 0
            for f in files:
                lang = f.get("language", "unknown").upper()
                lang_breakdown[lang] = lang_breakdown.get(lang, 0) + f.get("loc", 0)
                total_loc += f.get("loc", 0)
                
            breakdown_str = "\n".join([f"- **{lang}**: {loc} lines of code" for lang, loc in lang_breakdown.items()])
            avg_loc = round(total_loc / len(files), 1) if files else 0
            
            answer = (
                f"### 📊 Codebase Metrics & Statistics\n"
                f"- **Total Files:** {len(files)} files\n"
                f"- **Total LOC:** {total_loc} lines of code\n"
                f"- **Average File Size:** {avg_loc} LOC/file\n\n"
                f"**Language breakdown:**\n{breakdown_str}"
            )

        # 3.3. Architecture & Import Relationships
        elif any(k in query for k in ["architecture", "structure", "import graph", "imports", "topology", "relationship", "relations", "core module"]):
            import_graph = project_model.get("import_graph", {})
            indegree = {}
            for source, targets in import_graph.items():
                for target in targets:
                    indegree[target] = indegree.get(target, 0) + 1
                    
            sorted_imports = sorted(indegree.items(), key=lambda x: x[1], reverse=True)
            if not sorted_imports:
                answer = "I could not resolve any structural import relationships in this codebase."
            else:
                core_modules_str = "\n".join([f"- **[{module}]** - imported by **{count}** other files" for module, count in sorted_imports[:5]])
                answer = (
                    f"### 🏛️ Codebase Architecture & Relationships\n"
                    f"Here is an overview of the internal structure and dependencies in this project.\n\n"
                    f"**Core Codebase Modules (Most Imported):**\n{core_modules_str}\n\n"
                    f"**Import Topology Overview:**\n"
                    f"A total of **{len(import_graph)}** file-level import pathways were detected. "
                    f"You can view the full visual architecture topology in the standard GitHub-compatible Mermaid diagrams in the README."
                )
                sources = [m[0] for m in sorted_imports[:3]]
                
        # 4. Specific File Query
        else:
            matched_file = None
            for f in files:
                fname = os.path.basename(f["path"]).lower()
                if fname in query:
                    matched_file = f
                    break
                    
            if matched_file:
                classes = matched_file.get("classes", [])
                functions = matched_file.get("functions", [])
                classes_str = ", ".join([f"`{c['name']}`" for c in classes]) if classes else "none"
                funcs_str = ", ".join([f"`{fn['name']}`" for fn in functions]) if functions else "none"
                doc = matched_file.get("module_docstring") or "No module docstring provided."
                
                answer = (
                    f"### 📄 Module Overview: [{matched_file['path']}]\n"
                    f"- **Language:** {matched_file['language'].upper()}\n"
                    f"- **Lines of Code:** {matched_file['loc']} LOC\n"
                    f"- **Classes defined:** {classes_str}\n"
                    f"- **Functions defined:** {funcs_str}\n\n"
                    f"**Overview details:**\n> {doc}"
                )
                sources = [matched_file["path"]]
                
            # 5. Class / Symbol / Function Search
            else:
                matched_class = None
                matched_func = None
                def_file = ""
                for f in files:
                    for cls in f.get("classes", []):
                        if cls["name"].lower() in query:
                            matched_class = cls
                            def_file = f["path"]
                            break
                    for fn in f.get("functions", []):
                        if fn["name"].lower() in query:
                            matched_func = fn
                            def_file = f["path"]
                            break
                    if matched_class or matched_func:
                        break
                        
                if matched_class:
                    methods_str = ", ".join([f"`{m['name']}`" for m in matched_class.get("methods", [])]) if matched_class.get("methods") else "none"
                    answer = (
                        f"### 🏛️ Class: `{matched_class['name']}`\n"
                        f"- **Defined in:** [{def_file}#L{matched_class['line_number']}]\n"
                        f"- **Inherits from:** {', '.join(matched_class.get('base_classes', [])) or 'None'}\n"
                        f"- **Methods:** {methods_str}\n\n"
                        f"**Description:**\n> {matched_class.get('docstring') or 'No class description.'}"
                    )
                    sources = [def_file]
                elif matched_func:
                    args_str = ", ".join([f"`{p['name']}`" for p in matched_func.get("params", [])]) if matched_func.get("params") else "none"
                    answer = (
                        f"### ⚙️ Function: `{matched_func['name']}`\n"
                        f"- **Defined in:** [{def_file}#L{matched_func['line_number']}]\n"
                        f"- **Async:** `{matched_func.get('is_async', False)}`\n"
                        f"- **Parameters:** {args_str}\n"
                        f"- **Return type:** `{matched_func.get('return_type') or 'Any'}`\n\n"
                        f"**Description:**\n> {matched_func.get('docstring') or 'No description available.'}"
                    )
                    sources = [def_file]
                    
    # 6. Fallback BM25-like search over docstrings and paths
    if not answer:
        query_tokens = set([t for t in query.split() if len(t) > 2])
        if not query_tokens:
            answer = "Could you please elaborate on your question? You can ask me about dependencies, routes, technologies, or details of specific files/classes/functions in this codebase."
        else:
            rankings = []
            for f in files:
                score = 0
                path_lower = f["path"].lower()
                doc_lower = (f.get("module_docstring") or "").lower()
                
                for token in query_tokens:
                    if token in path_lower:
                        score += 5
                    if token in doc_lower:
                        score += 2
                        
                    for cls in f.get("classes", []):
                        if token in cls["name"].lower():
                            score += 4
                        if token in (cls.get("docstring") or "").lower():
                            score += 1
                    for fn in f.get("functions", []):
                        if token in fn["name"].lower():
                            score += 4
                        if token in (fn.get("docstring") or "").lower():
                            score += 1
                            
                if score > 0:
                    rankings.append((score, f))
                    
            rankings.sort(key=lambda x: x[0], reverse=True)
            if rankings:
                top_matches = rankings[:3]
                match_str = ""
                for score, f in top_matches:
                    match_str += f"- **[{f['path']}]** ({f['language']}, {f['loc']} LOC) - Relevance Score: {score}\n"
                    if f.get("module_docstring"):
                        short_doc = f["module_docstring"].split(".")[0][:120] + "..."
                        match_str += f"  *Overview:* {short_doc}\n"
                        
                answer = f"### 🔍 Relevant Codebase Matches\nI matched your question with these files in the codebase:\n\n{match_str}"
                sources = [f["path"] for _, f in top_matches]
                
    if not answer:
        answer = "I couldn't find any direct matches in the codebase for your question. Try asking about:\n- Specific files (e.g. `main.py`)\n- Class/Function names\n- Routes, stack, dependencies, or lines of code."

    # ── NDJSON Streaming Generator ───────────────────────────────────────────
    async def event_generator():
        # Yield the tokens of the answer word-by-word with a tiny delay to simulate streaming
        lines = answer.split("\n")
        for line_idx, line in enumerate(lines):
            line_words = line.split(" ")
            for word_idx, w in enumerate(line_words):
                space = " " if word_idx < len(line_words) - 1 else ""
                yield json.dumps({"token": w + space}) + "\n"
                await asyncio.sleep(0.003) # extremely fast but smooth typing
            if line_idx < len(lines) - 1:
                yield json.dumps({"token": "\n"}) + "\n"
                await asyncio.sleep(0.003)
                
        # Send sources metadata
        yield json.dumps({"sources": sources}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
