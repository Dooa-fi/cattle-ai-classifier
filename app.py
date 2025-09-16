import streamlit as st
import time
from PIL import Image
import pandas as pd
import io


from api_client import OpenRouterClient
from prompts import get_system_prompt

# Page configuration
st.set_page_config(
    page_title="Cattle AI Classifier",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables"""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

def process_uploaded_image(uploaded_file):
    """Process uploaded image and convert WEBP to JPEG if needed"""
    try:
        # Open image directly from uploaded file
        img = Image.open(uploaded_file)
        
        # Convert to RGB if needed (for WEBP or other formats)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save to memory buffer as JPEG
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        
        return img_buffer, img.size
    except Exception as e:
        st.error(f"Error processing image {uploaded_file.name}: {str(e)}")
        return None, None


# def convert_webp_to_jpeg(image_path: str) -> str:
#     """Convert WEBP image to JPEG for LLM compatibility"""
#     try:
#         path = Path(image_path)
#         if path.suffix.lower() == ".webp":
#             img = Image.open(image_path).convert("RGB")
#             jpeg_path = str(path.with_suffix(".jpeg"))
#             img.save(jpeg_path, "JPEG", quality=95)
#             return jpeg_path
#         return image_path
#     except Exception as e:
#         st.error(f"Error converting WEBP to JPEG: {str(e)}")
#         return image_path

def display_image_with_analysis(uploaded_file, image_size, analysis_result, index):
    """Display image alongside its analysis"""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(uploaded_file, caption=f"Image {index + 1}", width='stretch')
        
        # Image info
        if image_size:
            st.caption(f"Size: {image_size[0]}x{image_size[1]} pixels")

    
    with col2:
        if analysis_result.get("success"):
            st.success(f"✅ Analysis Complete (Model: {analysis_result['model_used']})")
            
            # Display analysis in expandable section
            with st.expander("📋 Full Analysis", expanded=True):
                st.write(analysis_result["analysis"])
            
            # Token usage info
            if analysis_result.get("tokens_used"):
                st.caption(f"Tokens used: {analysis_result['tokens_used']}")
        
        elif analysis_result.get("error"):
            st.error(f"❌ Analysis Failed: {analysis_result['error']}")
        else:
            st.info("⏳ Analysis pending...")

def export_results_to_excel():
    """Export analysis results to Excel"""
    if not st.session_state.analysis_results:
        st.warning("No results to export!")
        return
    
    # Prepare data for Excel
    excel_data = []
    for i, result in enumerate(st.session_state.analysis_results):
        if result.get("success"):
            excel_data.append({
                "Image Number": i + 1,
                "Image Name": st.session_state.uploaded_files[i]["name"],
                "Model Used": result["model_used"],
                "Analysis": result["analysis"],
                "Tokens Used": result.get("tokens_used", 0),
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

    
    if excel_data:
        df = pd.DataFrame(excel_data)
        
        # Create an Excel buffer
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Analysis Results')
        
        st.download_button(
            label="📥 Download Results as Excel",
            data=excel_buffer.getvalue(),
            file_name=f"cattle_analysis_results_{int(time.time())}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def main():
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("🐄 Cattle AI Classifier")
    st.markdown("**AI-powered breed recognition and type classification for cattle and buffaloes**")
    
    # Sidebar configuration
    st.sidebar.header("🛠️ Configuration")
    
    # API Key input
    # API Key input
    # Get API key from secrets (hidden from users)
    try:
        api_key = st.secrets["OPENROUTER_API_KEY"]
        if not api_key or api_key == "your_api_key_here":
            st.sidebar.error("⚠️ API key not configured!")
            st.error("🔧 Application configuration error. Please contact the administrator.")
            st.stop()
    except Exception as e:
        st.sidebar.error("⚠️ Configuration error!")
        st.error("🔧 Application configuration error. Please contact the administrator.")
        st.stop()

    
    # Initialize client
    client = OpenRouterClient(api_key)
    
    # Model selection
    available_models = client.get_available_models()
    selected_model = st.sidebar.selectbox(
        "🤖 Select AI Model",
        available_models,
        index=6,  # Default to qwen2.5-vl-32b-instruct:free
        help="Choose the AI model for analysis"
    )
    
    # Task type selection
    task_type = st.sidebar.radio(
        "📋 Analysis Type",
        ["breed_recognition", "type_classification"],
        format_func=lambda x: "🔍 Breed Recognition" if x == "breed_recognition" else "📊 Type Classification",
        help="Choose the type of analysis to perform"
    )
    
    # Main interface
    st.header("📤 Upload Images")
    
    uploaded_files = st.file_uploader(
        "Upload cattle/buffalo images for analysis",
        type=['png', 'jpg', 'jpeg', 'webp'],
        accept_multiple_files=True,
        help="You can upload up to 10 images at once"
    )
    
    # Process uploaded files
    if uploaded_files:
        if len(uploaded_files) > 10:
            st.warning("⚠️ Maximum 10 images allowed. Only the first 10 will be processed.")
            uploaded_files = uploaded_files[:10]
        
        # Save files and update session state if needed
        current_file_names = [f.name for f in uploaded_files]
        session_file_names = [f["name"] for f in st.session_state.uploaded_files]
        
        if current_file_names != session_file_names:
            # Clear previous results if files changed
            st.session_state.analysis_results = []
            st.session_state.uploaded_files = []
            
            # Process uploaded files in memory
            for uploaded_file in uploaded_files:
                img_buffer, img_size = process_uploaded_image(uploaded_file)
                if img_buffer:
                    st.session_state.uploaded_files.append({
                        "name": uploaded_file.name,
                        "buffer": img_buffer,
                        "size": img_size,
                        "original_file": uploaded_file
                    })

        
        # Analysis section
        st.header("🔬 Analysis Results")
        
        # Progress tracking
        total_files = len(st.session_state.uploaded_files)
        completed_analyses = len([r for r in st.session_state.analysis_results if r.get("success") or r.get("error")])
        
        # Analyze all button
        if st.button("🚀 Analyze All Images", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Get system prompt for selected task
            system_prompt = get_system_prompt(task_type)
            
            # Clear previous results
            st.session_state.analysis_results = []
            
            for i, file_info in enumerate(st.session_state.uploaded_files):
                status_text.text(f"Analyzing image {i+1}/{total_files}: {file_info['name']}")
                
                # Perform analysis using image buffer
                result = client.analyze_image_from_buffer(file_info["buffer"], selected_model, system_prompt)
                st.session_state.analysis_results.append(result)
                
                # Update progress
                progress_bar.progress((i + 1) / total_files)
                
                # Brief delay between requests
                time.sleep(1)
            
            status_text.text("✅ All analyses complete!")
            progress_bar.progress(1.0)
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()
        
        # Display results
        if st.session_state.analysis_results:
            # Summary statistics
            successful_analyses = len([r for r in st.session_state.analysis_results if r.get("success")])
            failed_analyses = len([r for r in st.session_state.analysis_results if r.get("error")])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Successful", successful_analyses)
            with col2:
                st.metric("❌ Failed", failed_analyses)
            with col3:
                st.metric("📊 Total", len(st.session_state.uploaded_files))
            
            # Export button
            if successful_analyses > 0:
                export_results_to_excel()
            
            st.divider()
            
            # Display individual results
            for i, (file_info, result) in enumerate(zip(st.session_state.uploaded_files, st.session_state.analysis_results)):
                with st.container():
                    display_image_with_analysis(file_info["original_file"], file_info["size"], result, i)
                    if i < len(st.session_state.uploaded_files) - 1:
                        st.divider()

        
        elif st.session_state.uploaded_files:
            st.info("👆 Click 'Analyze All Images' to start the analysis process.")
    
    # Footer information
    st.divider()
    with st.expander("ℹ️ About this Application"):
        st.markdown("""
        **Cattle AI Classifier** is designed to solve two key problem statements from the Ministry of Fisheries, Animal Husbandry & Dairying:
        
        1. **Problem Statement ID 25005**: Image-based Animal Type Classification for cattle and buffaloes
        2. **Problem Statement ID 25004**: Image-based breed recognition for cattle and buffaloes of India
        
        **Features:**
        - Upload up to 10 images for batch analysis
        - Choose from 12 free AI models via OpenRouter
        - Breed recognition for Indian cattle and buffalo breeds
        - Animal type classification for breeding assessment
        - Export results to Excel format
        - Secure in-memory image processing
        
        **Supported Models:**
        - Sonoma (Dusk/Sky Alpha)
        - Mistral Small (3.1/3.2 24B)
        - Meta Llama 4 (Maverick/Scout)
        - Qwen 2.5 Vision (32B/72B)
        - Google Gemma 3 (4B/12B/27B)
        - Moonshot Kimi Vision
        """)

if __name__ == "__main__":
    main()
