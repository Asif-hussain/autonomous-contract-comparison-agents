import streamlit as st
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow 'src' module imports
# This ensures imports work whether run from root or src directory
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import tempfile
import shutil
import json
from dotenv import load_dotenv

# Import core logic
from src.main import initialize_clients, process_contract_comparison, validate_environment
from src.models import ContractChangeOutput

# Page Config
st.set_page_config(
    page_title="Autonomous Contract Comparison",
    page_icon="⚖️",
    layout="wide"
)

# Load Env
load_dotenv()

def save_uploaded_file(uploaded_file):
    """Save an uploaded file to a temporary directory and return the path."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def main():
    st.title("⚖️ Autonomous Contract Comparison Agent")
    st.markdown("""
    Upload an **Original Contract** and an **Amendment** (images/PDFs) to automatically identify changes.
    """)

    # Sidebar for System Info
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # System Status in a nice container
        with st.container(border=True):
            st.subheader("System Status")
            if validate_environment():
                st.markdown("🟢 **API Keys**: Configured")
                st.markdown("🟢 **Tracing**: Active")
                st.caption("Ready for analysis")
            else:
                st.error("❌ Environment Issues Detected")
                st.stop()
        
        st.divider()
        
        # Model Info
        st.subheader("🤖 Model Info")
        st.info("Using **GPT-4o Vision**")
        st.markdown("""
        *   **Context**: 128k Tokens
        *   **Vision**: High Fidelity
        *   **Tracing**: Langfuse
        """)
        
        st.divider()

        # How it works expander
        with st.expander("ℹ️ How it works"):
            st.markdown("""
            1. **Uploads** are parsed by GPT-4o.
            2. **Agent 1** maps the structure.
            3. **Agent 2** extracts diffs.
            4. **Langfuse** traces the flow.
            """)
    
    # Main Input Area
    st.header("📄 Document Upload")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Contract")
        original_file = st.file_uploader("Upload Original Image/PDF", type=['png', 'jpg', 'jpeg', 'pdf'], key="original")
        if original_file:
            if original_file.type == "application/pdf":
                st.info("📄 PDF uploaded (will be converted to image)")
            else:
                st.image(original_file, caption="Original Contract Preview")

    with col2:
        st.subheader("Amendment Contract")
        amendment_file = st.file_uploader("Upload Amendment Image/PDF", type=['png', 'jpg', 'jpeg', 'pdf'], key="amendment")
        if amendment_file:
            if amendment_file.type == "application/pdf":
                st.info("📄 PDF uploaded (will be converted to image)")
            else:
                st.image(amendment_file, caption="Amendment Contract Preview")

    # Process Button
    if st.button("🔍 Compare Contracts", type="primary"):
        if not original_file or not amendment_file:
            st.warning("Please upload both contracts to proceed.")
            return

        with st.spinner("Initializing Agents... Parsing Images... Contextualizing... Extracting Changes..."):
            try:
                # 1. Save files to temp paths
                original_path = save_uploaded_file(original_file)
                amendment_path = save_uploaded_file(amendment_file)

                # 2. Init Clients
                openai_client, _ = initialize_clients()

                # 3. Process
                result, trace_id = process_contract_comparison(
                    original_image_path=original_path,
                    amendment_image_path=amendment_path,
                    openai_client=openai_client
                )

                # 4. Display Results
                st.divider()
                st.success("✅ Analysis Complete!")
                
                # Tracing Popover (as requested)
                if trace_id:
                    with st.popover("👁️ View Trace"):
                        st.markdown(f"**Trace ID**: `{trace_id}`")
                        st.markdown(f"[Open in Langfuse](https://cloud.langfuse.com/trace/{trace_id})")
                        st.info("Click the link above to view the full execution trace, including tokens, latency, and agent steps.")

                # Result Columns
                res_col1, res_col2 = st.columns([1, 1])

                with res_col1:
                    st.header("📋 Summary of Changes")
                    st.info(result.summary_of_the_change)
                
                with res_col2:
                    st.header("🎯 Change Details")
                    
                    st.subheader("Sections Changed")
                    for section in result.sections_changed:
                        st.markdown(f"- **{section}**")
                    
                    st.subheader("Topics Touched")
                    for topic in result.topics_touched:
                        st.markdown(f"- {topic}")

                # JSON Expander
                with st.expander("View Raw JSON Output"):
                    st.json(result.model_dump())

                # Cleanup
                os.unlink(original_path)
                os.unlink(amendment_path)

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
                # st.exception(e) # Uncomment for debug trace

if __name__ == "__main__":
    main()
