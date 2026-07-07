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
                
    # ── Rule-based router and advanced query engine ───────────────────────────
    answer = None
    sources = []
    
    # ── 1. Frontend / UI Specific Router ──────────────────────────────────────
    frontend_keywords = {"frontend", "ui", "component", "components", "css", "style", "styles", "styling", "layout", "visual", "react", "view", "page", "pages", "color", "theme", "button", "buttons", "template", "templates", "jsx", "html"}
    import re
    query_words = set(re.findall(r'\b\w+\b', query))
    if any(k in query_words for k in frontend_keywords):
        # Scan files for frontend components, templates, and styles
        react_components = []
        css_selectors = []
        html_details = []
        js_files = []
        css_files = []
        html_files = []
        
        for f in files:
            lang = f.get("language", "").lower()
            path = f.get("path", "")
            
            if lang in ("javascript", "typescript"):
                js_files.append(path)
                # Look for capitalized functions which usually represent React components
                for fn in f.get("functions", []):
                    name = fn.get("name", "")
                    if name and name[0].isupper():
                        react_components.append({
                            "name": name,
                            "path": path,
                            "line": fn.get("line_number", 1),
                            "doc": fn.get("docstring") or "React component"
                        })
                # Also check classes (could be class components)
                for cls in f.get("classes", []):
                    name = cls.get("name", "")
                    if name and name[0].isupper():
                        react_components.append({
                            "name": name,
                            "path": path,
                            "line": cls.get("line_number", 1),
                            "doc": cls.get("docstring") or "Class React Component"
                        })
            elif lang == "css":
                css_files.append(path)
                # Selectors are stored in 'imports' of css file
                for selector in f.get("imports", []):
                    css_selectors.append({
                        "selector": selector,
                        "path": path
                    })
            elif lang == "html":
                html_files.append(path)
                # Forms/links in HTML are mapped to 'imports'
                html_details.append({
                    "path": path,
                    "doc": f.get("module_docstring") or "HTML Template"
                })
                
        # Build a beautiful, comprehensive response about frontend UI structure
        ui_sections = []
        ui_sections.append("### 🎨 Frontend UI & Style Architecture")
        
        if not js_files and not css_files and not html_files:
            ui_sections.append("No dedicated frontend assets (JavaScript, HTML, CSS) were identified in this analysis.")
        else:
            ui_sections.append(f"The project includes frontend assets across **{len(js_files)}** JS/TS files, **{len(css_files)}** stylesheets, and **{len(html_files)}** HTML documents.")
            
            if react_components:
                ui_sections.append("\n**React/UI Components:**")
                for comp in react_components[:12]:
                    ui_sections.append(f"- `{comp['name']}` (defined in [{comp['path']}#L{comp['line']}]) - *{comp['doc']}*")
                if len(react_components) > 12:
                    ui_sections.append(f"- *and {len(react_components) - 12} more components...*")
                    
            if css_selectors:
                ui_sections.append("\n**Key Stylesheets & Custom Classes:**")
                for path in css_files[:3]:
                    selectors_in_file = [s['selector'] for s in css_selectors if s['path'] == path]
                    selectors_str = ", ".join([f"`{s}`" for s in selectors_in_file[:10]])
                    ui_sections.append(f"- **[{path}]**: Styles defined for {selectors_str}")
                    
            if html_details:
                ui_sections.append("\n**HTML Documents & Entry points:**")
                for html in html_details[:5]:
                    ui_sections.append(f"- **[{html['path']}]**: *{html['doc']}*")
                    
            # Explain how the front-end connects
            if frameworks:
                ui_sections.append(f"\n**UI Framework & Integration:** Detects framework **{', '.join(frameworks)}**. The UI coordinates state or queries backend APIs.")
                
        answer = "\n".join(ui_sections)
        sources = js_files[:2] + css_files[:1] + html_files[:1]
        
    # ── 2. Enhanced General Codebase Search & Answer Engine ─────────────────────
    if not answer:
        # Tokenize query to find relevant matches
        query_tokens = set([t for t in query.split() if len(t) > 2])
        is_followup = any(w in query for w in ["it", "its", "this", "describe", "explain", "detail", "more", "functions", "methods", "classes", "loc", "lines", "imports", "code", "show", "list"])
        
        # Check standard follow-up patterns first
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
                            
        # Dependency check
        if not answer and any(k in query for k in ["dependency", "dependencies", "package", "packages", "library", "libraries", "pip", "npm", "requirements"]):
            if not dependencies:
                answer = "No dependencies or package lists were detected in this codebase."
            else:
                dep_list_str = "\n".join([f"- **{d['name']}** (version: `{d.get('version') or '*'}`) - via *{d.get('source')}*" for d in dependencies])
                answer = f"### 📦 Detected Dependencies ({len(dependencies)})\nHere are the third-party libraries and packages used in this project:\n\n{dep_list_str}"
                
        # Files overview
        elif not answer and any(k in query for k in ["file", "files", "overview", "structure", "tree", "catalog", "directory"]):
            if not files:
                answer = "No files were detected in this codebase."
            else:
                file_list_str = "\n".join([f"- **{f['path']}** ({f['language']}, {f['loc']} LOC)" for f in files[:25]])
                if len(files) > 25:
                    file_list_str += f"\n- *and {len(files) - 25} more files...*"
                answer = f"### 📁 Codebase Files Overview ({len(files)} files)\nHere are the files detected in this codebase:\n\n{file_list_str}"
                
        # API Routes
        elif not answer and any(k in query for k in ["route", "routes", "endpoint", "endpoints", "api", "url", "urls", "path", "http"]):
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
                
        # Technology Stack
        elif not answer and any(k in query for k in ["framework", "frameworks", "stack", "technology", "technologies", "django", "flask", "fastapi", "react", "vue"]):
            if not frameworks:
                answer = "This appears to be a standard utility codebase. No major web frameworks (like FastAPI, Django, Flask, or React) were identified."
            else:
                fw_list_str = "\n".join([f"- **{fw}**" for fw in frameworks])
                answer = f"### 🛠️ Technology Stack\nThis codebase relies on the following frameworks/technologies:\n\n{fw_list_str}"
                
        # Entry points
        elif not answer and any(k in query for k in ["entry", "run", "start", "main", "launch", "execute", "executable"]):
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

        # Size Metrics
        elif not answer and any(k in query for k in ["loc", "lines", "size", "metrics", "count", "how big", "statistics"]):
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

        # Architecture & import relationships
        elif not answer and any(k in query for k in ["architecture", "structure", "import graph", "imports", "topology", "relationship", "relations", "core module"]):
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

        # Custom Search / Fallback
        if not answer:
            # 1. Direct name matches (Files, Classes, Functions)
            matched_file = None
            matched_class = None
            matched_func = None
            def_file = ""
            
            for f in files:
                fname = os.path.basename(f["path"]).lower()
                if fname in query:
                    matched_file = f
                    break
                    
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
            elif matched_class:
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
                
            # 2. General Query matching logic (BM25 token match / smart retrieval)
            if not answer and query_tokens:
                rankings = []
                for f in files:
                    score = 0
                    path_lower = f["path"].lower()
                    doc_lower = (f.get("module_docstring") or "").lower()
                    
                    # Accumulate scores based on token matches in path, docs, classes, functions, and parameters
                    matched_items = []
                    
                    for token in query_tokens:
                        if token in path_lower:
                            score += 10
                            matched_items.append(f"file path `{f['path']}`")
                        if token in doc_lower:
                            score += 4
                            matched_items.append("module documentation")
                            
                        for cls in f.get("classes", []):
                            cname = cls["name"].lower()
                            cdoc = (cls.get("docstring") or "").lower()
                            if token in cname:
                                score += 8
                                matched_items.append(f"class `{cls['name']}`")
                            if token in cdoc:
                                score += 3
                                matched_items.append(f"docstring of `{cls['name']}`")
                                
                        for fn in f.get("functions", []):
                            fname = fn["name"].lower()
                            fdoc = (fn.get("docstring") or "").lower()
                            if token in fname:
                                score += 8
                                matched_items.append(f"function `{fn['name']}`")
                            if token in fdoc:
                                score += 3
                                matched_items.append(f"docstring of `{fn['name']}`")
                                
                            for param in fn.get("params", []):
                                if token in param["name"].lower():
                                    score += 2
                                    matched_items.append(f"parameter `{param['name']}` in `{fn['name']}`")
                                    
                        # Handle CSS selectors for stylesheet files
                        if f.get("language") == "css":
                            for selector in f.get("imports", []):
                                if token in selector.lower():
                                    score += 6
                                    matched_items.append(f"CSS selector `{selector}`")
                                    
                    if score > 0:
                        rankings.append({
                            "score": score,
                            "file": f,
                            "matched_reasons": list(set(matched_items))
                        })
                        
                rankings.sort(key=lambda x: x["score"], reverse=True)
                if rankings:
                    top_matches = rankings[:4]
                    results_lines = []
                    results_lines.append(f"### 🔍 Search results matching your query")
                    results_lines.append(f"I found the following matching items and files in the codebase:\n")
                    
                    for idx, item in enumerate(top_matches, 1):
                        f = item["file"]
                        reasons = ", ".join(item["matched_reasons"][:3])
                        loc_info = f"({f.get('language', '').upper()}, {f.get('loc', 0)} LOC)"
                        results_lines.append(f"{idx}. **[{f['path']}]** {loc_info}")
                        results_lines.append(f"   - *Matches found in:* {reasons}")
                        
                        # Add docstring snippets if available
                        doc = f.get("module_docstring")
                        if doc:
                            short_doc = doc.split(".")[0][:120] + "..."
                            results_lines.append(f"   - *Overview:* {short_doc}")
                            
                        # Add classes / functions list if relevant
                        if f.get("classes"):
                            class_names = ", ".join([f"`{c['name']}`" for c in f["classes"][:5]])
                            results_lines.append(f"   - *Classes:* {class_names}")
                        if f.get("functions"):
                            func_names = ", ".join([f"`{fn['name']}`" for fn in f["functions"][:8]])
                            results_lines.append(f"   - *Functions:* {func_names}")
                        results_lines.append("")
                        
                    answer = "\n".join(results_lines)
                    sources = [item["file"]["path"] for item in top_matches]
                    
        if not answer:
            answer = "I couldn't find any direct matches in the codebase for your question. Try asking about:\n- Specific files (e.g. `main.py`)\n- Class/Function/Component names\n- Frontend UI styling, CSS classes, or React components\n- Routes, stack, dependencies, or lines of code."

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
