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

def get_strict_title(path, text_content):
    """
    Hybrid Title Extraction (Strict Mode).
    Priority 1: Clean, Valid Metadata (Must be text, not numbers).
    Priority 2: Largest Font on Page 1 (Visual Title) with Clustering.
    """
    try:
        doc = fitz.open(path)

        # --- Strategy 1: Metadata (Priority) ---
        meta_title = doc.metadata.get("title", "").strip()

        # Strict Metadata Validation
        if meta_title and len(meta_title) > 5:
            # Reject pure numbers or IDs
            if re.match(r"^[\d\s\.\-_]+$", meta_title):
                pass
            # Titles are rarely longer than 200 characters (~30 words)
            elif len(meta_title) > 200:
                pass
            else:
                # Check for common junk metadata
                junk_patterns = [
                    r"^microsoft word", r"^untitled", r"^latex", r"^presentation",
                    r"\.pdf$", r"\.docx?$", r"^slide", r"^document\d*$", r"^paper\d*$"
                ]
                is_junk = False
                for pat in junk_patterns:
                    if re.search(pat, meta_title, re.IGNORECASE):
                        is_junk = True
                        break

                if not is_junk:
                    doc.close()
                    return meta_title

        # --- Strategy 2: Visual Title (Fallback) ---
        page = doc[0]
        blocks = page.get_text("dict")["blocks"]
        doc.close()

        candidates = []

        for b in blocks:
            if "lines" not in b: continue
            for l in b["lines"]:
                for s in l["spans"]:
                    text = s["text"].strip()
                    size = s["size"]
                    # bbox is (x0, y0, x1, y1)
                    y_pos = s["bbox"][1]
                    height = s["bbox"][3] - s["bbox"][1]

                    # Filter out obvious noise
                    if len(text) < 3: continue
                    if re.match(r"^[\d\s\.\-_]+$", text): continue

                    # Filter out common header info
                    if re.search(
                        r"^(doi|issn|http|www|vol\.|no\.|pp\.|page|date|accepted|received|copyright|license|downloaded from)",
                        text, re.IGNORECASE): continue

                    candidates.append({
                        "text": text,
                        "size": size,
                        "y": y_pos,
                        "height": height
                    })

        if not candidates:
            return "Unknown Title"

        # Sort by size (descending) to find the "Title Font"
        candidates.sort(key=lambda x: x["size"], reverse=True)

        max_size = candidates[0]["size"]

        # Stricter tolerance: Only 1% difference allowed to avoid mixing Title (14pt) with Authors (12pt)
        title_spans = [c for c in candidates if c["size"] > max_size * 0.99]

        # Sort by vertical position (top to bottom)
        title_spans.sort(key=lambda x: x["y"])

        # --- CLUSTERING LOGIC ---
        final_parts = []
        if title_spans:
            final_parts.append(title_spans[0]["text"])
            last_y = title_spans[0]["y"]
            last_height = title_spans[0]["height"]

            for i in range(1, len(title_spans)):
                current = title_spans[i]
                gap = current["y"] - (last_y + last_height)

                # 1. Vertical Gap: Tighter threshold.
                if gap > last_height * 1.3:
                    break

                # 2. Content Heuristics
                txt = current["text"].lower()
                if "@" in txt or "email" in txt: break
                if any(kw in txt for kw in ["university", "institute", "department", "laboratory"]): break
                if any(kw in txt for kw in ["received", "accepted", "correspondence"]): break

                # 3. Author List Detection
                if current["text"].count(",") > 2:
                    break

                # Detect "A. Name" or "Name A." patterns
                if len(re.findall(r"\b[A-Z]\.\s?[A-Z]", current["text"])) > 1:
                    break

                final_parts.append(current["text"])
                last_y = current["y"]
                last_height = current["height"]

        # Join the text
        title = " ".join(final_parts)
        title = re.sub(r"\s+", " ", title).strip()

        # Sanity check fallback
        if (len(title) < 5 or re.match(r"^[\d\s]+$", title)) and len(candidates) > 1:
            # Try next largest font group...
            remaining = [c for c in candidates if c["size"] <= max_size * 0.99]
            if remaining:
                max_size_2 = remaining[0]["size"]
                title_spans_2 = [c for c in remaining if c["size"] > max_size_2 * 0.99]
                title_spans_2.sort(key=lambda x: x["y"])

                # Simple join for fallback
                title_2 = " ".join([s["text"] for s in title_spans_2])
                title_2 = re.sub(r"\s+", " ", title_2).strip()

                if len(title_2) > 5 and not re.match(r"^[\d\s]+$", title_2):
                    return title_2

        return title

    except Exception as e:
        print(f"Title Error: {e}")
        return "Unknown Title"

def extract_emails(text):
    """Extracts unique emails from text."""
    emails = EMAIL_RE.findall(text)
    seen = set()
    unique_emails = []
    for e in emails:
        e_lower = e.lower()
        if e_lower not in seen:
            seen.add(e_lower)
            unique_emails.append(e_lower)
    return unique_emails

def process_single_pdf(file_bytes, file_name, exclude_no_email=True):
    """
    Main orchestration logic for a single PDF.
    This is encapsulated so it can be called in parallel.
    """
    import tempfile
    import os

    results = []
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # 1. Get Text
        full_text = extract_text_content(tmp_path)

        if full_text:
            # 2. Get Data
            title = get_strict_title(tmp_path, full_text)
            emails = extract_emails(full_text)

            # 3. Add to results
            if emails:
                for email in emails:
                    results.append({
                        "File Name": file_name,
                        "Exact Title": title,
                        "Email": email
                    })
            else:
                if not exclude_no_email:
                    results.append({
                        "File Name": file_name,
                        "Exact Title": title,
                        "Email": "No Email Found"
                    })
        else:
            if not exclude_no_email:
                results.append({
                    "File Name": file_name,
                    "Exact Title": "Unreadable PDF",
                    "Email": "Error"
                })

    except Exception as e:
        return [{"File Name": file_name, "Exact Title": "Error", "Email": str(e)}]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    
    return results
