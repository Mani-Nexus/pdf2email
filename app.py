import streamlit as st
import pandas as pd
import concurrent.futures
from src.ui.styles import apply_custom_styles
from src.core.extractor import process_single_pdf
from src.utils.file_handler import to_excel

# Apply global styles
apply_custom_styles()

# ==========================================
# UI LAYOUT
# ==========================================

st.title("🎯 Precision PDF Extractor")
st.markdown("### Extract **Exact Titles** and **Emails** strictly.")
st.markdown("Upload PDFs or a **ZIP file**. Processing is now in **Hyper-Drive Mode** (1,000+ docs supported).")

# Settings
col1, col2 = st.columns([1, 1])
with col1:
    exclude_no_email = st.checkbox(
        "Exclude files with no emails", 
        value=True,
        help="If checked, files without any extracted emails will not be added to the final list."
    )
with col2:
    max_workers = st.slider(
        "Parallel Processing Threads", 
        min_value=1, 
        max_value=500, 
        value=64,
        help="Higher values process files faster. Recommended: 100+ for large batches on high-core VPS."
    )

uploaded_files = st.file_uploader("Upload PDFs or ZIP", type=["pdf", "zip"], accept_multiple_files=True)

if uploaded_files:
    st.divider()
    
    total_files = len(uploaded_files)
    results = []
    
    # Logic for parallel processing
    if st.button("🚀 Start High-Speed Extraction"):
        import time
        import zipfile
        from io import BytesIO
        
        start_time = time.time()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1. Prepare file data (expand ZIPs if present)
        file_data = [] # List of (bytes, name)
        
        for f in uploaded_files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(BytesIO(f.getvalue())) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf"):
                            file_data.append((z.read(name), name))
            else:
                file_data.append((f.getvalue(), f.name))
        
        total_extracted = len(file_data)
        if total_extracted == 0:
            st.error("No PDFs found in the selection or ZIP files.")
        else:
            status_text.text(f"Preparing {total_extracted} files for processing...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(process_single_pdf, data, name, exclude_no_email): name 
                    for data, name in file_data
                }
                
                completed = 0
                for future in concurrent.futures.as_completed(future_to_file):
                    try:
                        res = future.result()
                        results.extend(res)
                    except Exception as exc:
                        st.error(f"Batch error: {exc}")
                    
                    completed += 1
                    if completed % 5 == 0 or completed == total_extracted:
                        progress_bar.progress(completed / total_extracted)
                        status_text.text(f"Extracted {completed}/{total_extracted} documents...")

            duration = time.time() - start_time
            status_text.empty()
            progress_bar.empty()
            st.success(f"✅ Processed {total_extracted} files in {duration:.2f} seconds ({total_extracted/duration:.1f} files/sec)")

        # --- Display Results ---
        if results:
            df = pd.DataFrame(results)
            st.success(f"✅ Successfully processed {total_files} files.")

            # Interactive Table
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "File Name": st.column_config.TextColumn("File Name", width="medium"),
                    "Exact Title": st.column_config.TextColumn("Document Title", width="large"),
                    "Email": st.column_config.TextColumn("Email Address", width="medium"),
                }
            )

            # Download Button
            excel_data = to_excel(df)
            st.download_button(
                label="⬇️ Download Results (Excel)",
                data=excel_data,
                file_name="extracted_emails_titles.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data could be extracted from the uploaded files.")

else:
    st.info("👆 Upload files to begin extraction.")
