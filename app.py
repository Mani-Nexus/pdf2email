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
        import gc
        
        start_time = time.time()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # --- Memory-Safe File Data Generator ---
        def get_file_data(uploaded_files):
            for f in uploaded_files:
                if f.name.endswith(".zip"):
                    try:
                        with zipfile.ZipFile(BytesIO(f.getvalue())) as z:
                            for name in z.namelist():
                                if name.lower().endswith(".pdf"):
                                    # Yield one file at a time to save memory
                                    yield z.read(name), name
                    except Exception as ze:
                        st.error(f"Error reading ZIP {f.name}: {ze}")
                else:
                    yield f.getvalue(), f.name

        # For progress tracking, we still need a total count
        # This is a trade-off: counting first vs estimating
        # We'll estimate based on uploaded_files or count if not too large
        status_text.text("Scanning upload for PDFs...")
        
        # Convert generator to a list in small chunks or just process directly
        # To avoid RAM spike, we'll process in chunks of 50
        CHUNK_SIZE = 50
        all_file_data_gen = get_file_data(uploaded_files)
        
        completed = 0
        total_found = 0
        
        # We'll use a loop to pull chunks from the generator and process them
        while True:
            chunk = []
            try:
                for _ in range(CHUNK_SIZE):
                    chunk.append(next(all_file_data_gen))
            except StopIteration:
                pass
            
            if not chunk:
                break
                
            total_found += len(chunk)
            status_text.text(f"Processing batch of {len(chunk)} (Total: {total_found})...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(process_single_pdf, data, name, exclude_no_email): name 
                    for data, name in chunk
                }
                
                for future in concurrent.futures.as_completed(future_to_file):
                    file_name = future_to_file[future]
                    try:
                        res = future.result()
                        results.extend(res)
                    except Exception as exc:
                        st.error(f"Error in {file_name}: {exc}")
                        print(f"ERROR: {file_name} -> {exc}") # Server-side log
                    
                    completed += 1
                    # Update progress bar occasionally
                    if completed % 10 == 0:
                        progress_bar.progress(min(completed / (len(uploaded_files) * 5), 0.99)) # Estimated progress
            
            # Explicit Garbage Collection after each chunk
            del chunk
            gc.collect()

        duration = time.time() - start_time
        status_text.empty()
        progress_bar.empty()
        
        if total_found > 0:
            st.success(f"✅ Processed {total_found} files in {duration:.2f} seconds ({total_found/duration:.1f} files/sec)")
        else:
            st.warning("No PDFs found to process.")

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
