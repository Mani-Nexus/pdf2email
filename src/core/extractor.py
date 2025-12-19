import pdfplumber
import fitz  # PyMuPDF
import re

# Regex for Email
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def extract_text_content(path):
    """
    Extremely fast text extraction using PyMuPDF (fitz) as primary engine.
    Falls back to pdfplumber ONLY if fitz fails to find enough text.
    """
    text = ""
    # 1. Try PyMuPDF (fitz) - High performance C engine
    try:
        doc = fitz.open(path)
        for p in doc[:6]: # Scan first 6 pages
            text += p.get_text("text") + "\n"
        doc.close()
    except Exception:
        pass

    # 2. Hard Fallback to pdfplumber ONLY if fitz yields almost nothing
    if len(text.strip()) < 50:
        try:
            with pdfplumber.open(path) as pdf:
                for p in pdf.pages[:6]:
                    t = p.extract_text()
                    if t:
                        text += t + "\n"
        except Exception:
            pass

    return text.strip()

def extract_from_doc(doc, exclude_no_email=True):
    """
    Hyper-optimized extraction. Stops as soon as data is found.
    """
    # 1. Quick Metadata Title Attempt
    title = _get_title_from_doc(doc, metadata_only=True)
    
    unique_emails = []
    text = ""
    
    # 2. Sequential Page Scanning with Early Exit
    for p in doc[:6]:
        p_text = p.get_text("text")
        text += p_text + "\n"
        
        # Immediate Email Search
        found_emails = EMAIL_RE.findall(p_text)
        for e in found_emails:
            e_lower = e.lower()
            if e_lower not in unique_emails:
                unique_emails.append(e_lower)
        
        # AGGRESSIVE EARLY EXIT: If we have a title (from metdaata) and 2+ emails, stop now
        if title != "Unknown Title" and len(unique_emails) >= 2:
            break

    # 3. Final Visual Title Fallback if metadata failed
    if title == "Unknown Title":
        title = _get_title_from_doc(doc, metadata_only=False)

    if not unique_emails and exclude_no_email:
        return []

    if not unique_emails:
        return [{"Exact Title": title, "Email": "No Email Found"}]

    return [{"Exact Title": title, "Email": email} for email in unique_emails]

def _get_title_from_doc(doc, metadata_only=False):
    """Internal helper to extract title from a fitz Document."""
    try:
        # Strategy A: Metadata (Instant)
        meta_title = doc.metadata.get("title", "").strip()
        if meta_title and 5 < len(meta_title) < 200:
            if not re.match(r"^[\d\s\.\-_]+$", meta_title):
                junk_patterns = [r"^microsoft word", r"^untitled", r"^latex", r"^presentation", r"\.pdf$", r"\.docx?$", r"^slide"]
                if not any(re.search(pat, meta_title, re.IGNORECASE) for pat in junk_patterns):
                    return meta_title
        
        if metadata_only: return "Unknown Title"

        # Strategy B: Visual check (Page 1)
        page = doc[0]
        blocks = page.get_text("dict")["blocks"]
        candidates = []
        for b in blocks:
            if "lines" not in b: continue
            for l in b["lines"]:
                for s in l["spans"]:
                    text = s["text"].strip()
                    if len(text) < 3 or re.match(r"^[\d\s\.\-_]+$", text): continue
                    if re.search(r"^(doi|issn|http|www|vol\.|no\.)", text, re.IGNORECASE): continue
                    candidates.append({"text": text, "size": s["size"], "y": s["bbox"][1], "height": s["bbox"][3] - s["bbox"][1]})

        if not candidates: return "Unknown Title"
        
        candidates.sort(key=lambda x: x["size"], reverse=True)
        max_size = candidates[0]["size"]
        title_spans = [c for c in candidates if c["size"] > max_size * 0.98]
        title_spans.sort(key=lambda x: x["y"])

        final_parts = []
        if title_spans:
            final_parts.append(title_spans[0]["text"])
            last_y, last_h = title_spans[0]["y"], title_spans[0]["height"]
            for i in range(1, len(title_spans)):
                curr = title_spans[i]
                if (curr["y"] - (last_y + last_h)) > last_h * 1.5: break # Significant gap
                if any(kw in curr["text"].lower() for kw in ["university", "@", "email", "received"]): break
                final_parts.append(curr["text"])
                last_y, last_h = curr["y"], curr["height"]

        return re.sub(r"\s+", " ", " ".join(final_parts)).strip() or "Unknown Title"
    except Exception:
        return "Unknown Title"

def process_single_pdf(file_content, file_name, exclude_no_email=True):
    """
    High-performance extraction from memory bytes.
    Avoids temporary files and redundant opening.
    """
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        results = extract_from_doc(doc, exclude_no_email)
        doc.close()
        
        # Add filename to results
        for r in results:
            r["File Name"] = file_name
        return results
    except Exception as e:
        return [{"File Name": file_name, "Exact Title": "Error", "Email": str(e)}]
