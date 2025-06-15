import streamlit as st
import time
import os
import sys
import asyncio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.ai import process_speech_to_text, determine_report_type_from_transcript, extract_entities_from_text
from app.utils.reports import load_report_templates, save_report_to_history, format_report_for_display, send_cot_tcp, send_cot_pytak_sync
from app.utils.audio import get_audio_from_microphone
from app.utils.validators import validate_ip_address, validate_port
from app.utils.pytak_client import VoxFieldPyTAKClient
from app.utils.pytak_sender import send_cot_pytak, send_cot_direct
from app.utils.location import get_location_with_fallback

# Set page configuration
st.set_page_config(
    page_title="VoxField",
    page_icon="🔊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state variables if they don't exist
if 'translated_transcript' not in st.session_state:
    st.session_state.translated_transcript = None
if 'audio_language' not in st.session_state:
    st.session_state.audio_language = "et"  # Default to Estonian
if 'translate_to_english' not in st.session_state:
    st.session_state.translate_to_english = True  # Default to translating
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'report_data' not in st.session_state:
    st.session_state.report_data = {}
if 'report_history' not in st.session_state:
    st.session_state.report_history = []
if 'detected_report_type' not in st.session_state:
    st.session_state.detected_report_type = None
if 'detection_confidence' not in st.session_state:
    st.session_state.detection_confidence = 0
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

# Initialize server configuration in session state
if 'server_ip' not in st.session_state:
    st.session_state.server_ip = "239.2.3.1"
if 'server_port' not in st.session_state:
    st.session_state.server_port = 6969
if 'connection_type' not in st.session_state:
    st.session_state.connection_type = "UDP"
if 'server_configured' not in st.session_state:
    st.session_state.server_configured = False

# Add to session state initialization
if 'whisper_model' not in st.session_state:
    st.session_state.whisper_model = "default"  # or "estonian" for the Estonian model

# Load report templates
report_templates = load_report_templates()

def main():
    #FOR TESTING PURPOSES ONLY
    # Define TAK server IP and port
    # In production, these should be set via environment variables or configuration files
    #ip="192.168.1.194"
    #ip="192.168.1.161"
    #ip="239.2.3.1."
    #port=6969
    
    # Simple header
    st.title("VoxField - Voice-Enabled Military Reporting for TAK")
    
    # Server Configuration Section
    with st.expander("⚙️ TAK Server Configuration", expanded=not st.session_state.server_configured):
        st.markdown("### Connection Settings")
        
        col_config1, col_config2, col_config3 = st.columns([2, 1, 1])
        
        with col_config1:
            # IP Address input
            ip_input = st.text_input(
                "Server IP Address",
                value=st.session_state.server_ip,
                help="Enter the TAK server IP address or multicast address (e.g., 239.2.3.1)",
                placeholder="192.168.1.100 or 239.2.3.1"
            )
        
        with col_config2:
            # Port input
            port_input = st.text_input(
                "Port",
                value=str(st.session_state.server_port),
                help="Enter the TAK server port (typically 6969 for multicast, 8087 for TCP)",
                placeholder="6969"
            )
        
        with col_config3:
            # Connection type selection
            conn_type = st.selectbox(
                "Protocol",
                options=["UDP", "TCP"],
                index=0 if st.session_state.connection_type == "UDP" else 1,
                help="Select the connection protocol"
            )
        
        # Add preset configurations for common setups
        st.markdown("#### Quick Presets")
        preset_col1, preset_col2, preset_col3 = st.columns(3)
        
        with preset_col1:
            if st.button("📡 Multicast (Default)", use_container_width=True):
                st.session_state.server_ip = "239.2.3.1"
                st.session_state.server_port = 6969
                st.session_state.connection_type = "UDP"
                st.rerun()
        
        with preset_col2:
            if st.button("🖥️ TAK Server (TCP)", use_container_width=True):
                st.session_state.server_ip = "192.168.1.100"
                st.session_state.server_port = 8087
                st.session_state.connection_type = "TCP"
                st.rerun()
        
        with preset_col3:
            if st.button("🌐 FreeTAKServer", use_container_width=True):
                st.session_state.server_ip = "192.168.1.100"
                st.session_state.server_port = 8087
                st.session_state.connection_type = "TCP"
                st.rerun()
        
        # Validation and save button
        col_save1, col_save2 = st.columns([3, 1])
        
        with col_save2:
            if st.button("💾 Save Configuration", type="primary", use_container_width=True):
                # Validate inputs
                if not validate_ip_address(ip_input):
                    st.error("Invalid IP address format. Please enter a valid IPv4 address.")
                elif not validate_port(port_input):
                    st.error("Invalid port number. Please enter a port between 1 and 65535.")
                else:
                    # Save configuration
                    st.session_state.server_ip = ip_input
                    st.session_state.server_port = int(port_input)
                    st.session_state.connection_type = conn_type
                    st.session_state.server_configured = True
                    st.success(f"✅ Configuration saved! Connecting to {conn_type}://{ip_input}:{port_input}")
                    time.sleep(1)
                    st.rerun()
        with col_save1:
            st.markdown("⚙️ Speech Recognition Settings")
            
            model_option = st.selectbox("Whisper Model",
                options=["Standard", "Estonian-Optimized"],
                help="Estonian-Optimized model provides better accuracy for Estonian language"
            )
            st.session_state.use_estonian_model = (model_option == "Estonian-Optimized")
        
        # Display current configuration status
        if st.session_state.server_configured:
            st.info(f"**Current Configuration:** {st.session_state.connection_type}://{st.session_state.server_ip}:{st.session_state.server_port}")
    
    # Add a divider between configuration and main interface
    st.markdown("---")
    
    # Main interface - only show if server is configured
    if not st.session_state.server_configured:
        st.warning("⚠️ Please configure the TAK server connection above before proceeding.")
        return
    
    # Create a two-column layout for the main interface
    col1, col2 = st.columns([1, 1])
    
    with col1:

        st.markdown("### Language Settings")
        lang_col1, lang_col2 = st.columns(2)
        with lang_col1:
            st.session_state.audio_language = st.selectbox(
                "Speaking Language",
                options=["et", "en"],
                format_func=lambda x: {"et": "Estonian 🇪🇪", "en": "English 🇬🇧"}[x],
                index=0 if st.session_state.audio_language == "et" else 1,
                help="Select the language you'll be speaking"
            )
        
        with lang_col2:
            # Only show translation option if Estonian is selected
            if st.session_state.audio_language == "et":
                st.session_state.translate_to_english = st.checkbox(
                    "Translate to English",
                    value=st.session_state.translate_to_english,
                    help="Automatically translate Estonian to English for report processing"
                )
            else:
                st.info("Speaking in English")
        # 1. Large Push-to-Talk Button
        st.markdown("### Record Your Report")

    
        
        # Create a visually prominent recording button
        audio_container = st.container()
        with audio_container:
            # Audio recording with prominent styling
            st.markdown("""
            <style>
            div.stButton > button {
                width: 100%;
                height: 120px;
                font-size: 24px;
                background-color: #e8b62c;
                color: white;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Audio recording interface
            st.session_state.audio_data = get_audio_from_microphone(key="main_record")
            
            # 2. Real-time Transcription Display
            if st.session_state.audio_data:
                # Show audio playback control
                st.audio(st.session_state.audio_data, format="audio/wav")
                
                # Process button with spinner for feedback
                if st.button("Process Recording", key="process_recording", use_container_width=True):
                    with st.spinner("Transcribing audio..."):
                        # Process speech to text with translation
                        transcript, translated = process_speech_to_text(
                            st.session_state.audio_data,
                            language=st.session_state.audio_language,
                            translate_to_english=(st.session_state.translate_to_english and st.session_state.audio_language == "et")
                        )
                        st.session_state.transcript = transcript
                        st.session_state.translated_transcript = translated
                        
                        # Show language processing info
                        if translated:
                            st.success("✅ Transcribed from Estonian and translated to English!")
                        else:
                            st.success("✅ Transcription complete!")
                    
                    with st.spinner("Analyzing report type..."):
                        # Use translated transcript for analysis if available
                        analysis_transcript = translated if translated else transcript
                        report_type, confidence = determine_report_type_from_transcript(
                            transcript, 
                            translated
                        )
                        st.session_state.detected_report_type = report_type
                        st.session_state.detection_confidence = confidence
                    
                    with st.spinner("Preparing report template..."):
                        # Extract entities using the English transcript for better accuracy
                        working_transcript = translated if translated else transcript
                        st.session_state.report_data = extract_entities_from_text(
                            report_type,
                            working_transcript,
                            transcript  # Pass original as fallback
                        )
            
            # Update the transcript display section:
            if st.session_state.transcript:
                st.markdown("### Transcript")
                
                # Show both transcripts if translation occurred
                if st.session_state.translated_transcript:
                    # Create tabs for original and translated
                    tab1, tab2 = st.tabs(["Original (Estonian)", "Translated (English)"])
                    
                    with tab1:
                        transcript_container = st.container()
                        with transcript_container:
                            st.markdown("""
                            <style>
                            .transcript-box {
                                background-color: #f0f2f6;
                                border-radius: 10px;
                                padding: 20px;
                                margin-top: 10px;
                                margin-bottom: 20px;
                                border-left: 5px solid #4CAF50;
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"<div class='transcript-box'>{st.session_state.transcript}</div>", 
                                    unsafe_allow_html=True)
                    
                    with tab2:
                        transcript_container = st.container()
                        with transcript_container:
                            st.markdown("""
                            <style>
                            .translation-box {
                                background-color: #e8f4fd;
                                border-radius: 10px;
                                padding: 20px;
                                margin-top: 10px;
                                margin-bottom: 20px;
                                border-left: 5px solid #2196F3;
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"<div class='translation-box'>{st.session_state.translated_transcript}</div>", 
                                    unsafe_allow_html=True)
                else:
                    # Show single transcript
                    transcript_container = st.container()
                    with transcript_container:
                        st.markdown("""
                        <style>
                        .transcript-box {
                            background-color: #f0f2f6;
                            border-radius: 10px;
                            padding: 20px;
                            margin-top: 10px;
                            margin-bottom: 20px;
                            border-left: 5px solid #4CAF50;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"<div class='transcript-box'>{st.session_state.transcript}</div>", 
                                unsafe_allow_html=True)

    
    with col2:
        # 3. Report Preview Pane
        st.markdown("### Report Preview")
        
        if st.session_state.detected_report_type and st.session_state.report_data:
            report_type = st.session_state.detected_report_type
            template = report_templates[report_type]
            
            # Report type with confidence
            st.info(f"Detected Report Type: **{template['title']}** (Confidence: {st.session_state.detection_confidence:.2f})")
            
            # Allow changing the report type if needed
            new_report_type = st.selectbox(
                "Change report type if needed:",
                options=list(report_templates.keys()),
                format_func=lambda x: report_templates[x]['title'],
                index=list(report_templates.keys()).index(report_type)
            )
            
            if new_report_type != report_type:
                with st.spinner("Re-analyzing with new report type..."):
                    st.session_state.detected_report_type = new_report_type
                    st.session_state.report_data = extract_entities_from_text(
                        new_report_type,
                        st.session_state.transcript
                    )
                report_type = new_report_type
            
            # GET LOCATION OF SENDER
            with st.spinner("Getting sender location..."):
                sender_location = get_location_with_fallback()
                # Store in session state
                st.session_state.sender_location = sender_location
                # Display sender location info
                if sender_location['lat'] != 0 or sender_location['lon'] != 0:
                    accuracy_text = "High accuracy" if sender_location['ce'] < 100 else "Approximate"
                    st.success(f"📍 Sender location acquired: {sender_location['lat']:.6f}, {sender_location['lon']:.6f} ({accuracy_text})")
                else:
                    st.warning("📍 Could not get automatic location. Using default coordinates.")
            
            # Create an editable form for the report data
            with st.form("report_form"):
                # Display each field for editing
                for field in report_templates[report_type]["fields"]:
                    field_id = field["id"]
                    field_label = field["label"]
                    required = field["required"]
                    
                    current_value = st.session_state.report_data.get(field_id, "")
                    
                    # Add field with appropriate styling for required fields
                    new_value = st.text_input(
                        f"{field_label}{' *' if required else ''}",
                        value=current_value,
                        key=f"field_{field_id}"
                    )
                    
                    # Update the value in session state
                    if new_value != current_value:
                        st.session_state.report_data[field_id] = new_value
                
                # Form submission buttons
                send_btn = st.form_submit_button("Send Report", use_container_width=True)
                
            if send_btn:
                # Validate required fields
                report_type = st.session_state.detected_report_type
                template = report_templates[report_type]
                required_fields = [field["id"] for field in template["fields"] if field["required"]]
                
                missing_fields = []
                for field_id in required_fields:
                    if not st.session_state.report_data.get(field_id):
                        missing_fields.append(field_id)
                
                if missing_fields:
                    # Show error for missing fields
                    field_names = [next(field["label"] for field in template["fields"] if field["id"] == field_id) 
                                  for field_id in missing_fields]
                    st.error(f"Please fill in all required fields: {', '.join(field_names)}")
                else:
                    # Send the report (simulated)
                    with st.spinner("Sending report..."):
                        time.sleep(0.5)
                        
                        # Format the report for display and generate TAK CoT XML
                        formatted_report = format_report_for_display(report_type, st.session_state.report_data)
                        #formatted_report = format_report_for_display(report_type, st.session_state.report_data)
                        
                        #if send_result:
                        #    # Show success message about the report and generated files
                        #    success_msg = f"Report sent successfully via {st.session_state.connection_type}!"
                        #    if xml_file_path:
                        #        success_msg += " TAK CoT XML generated for WinTAK import."
                        #    st.success(success_msg)
                        #    report_status = "Sent"
                        #else:
                        #    st.error(f"Failed to send report to TAK server at {st.session_state.server_ip}:{st.session_state.server_port}. Please check your connection and configuration.")
                        #    report_status = "Failed"
                        
                        # Send CoT to TAK using the actual report data
                        print(f"Sending report to: {st.session_state.server_ip}:{st.session_state.server_port} via {st.session_state.connection_type}")
                        if send_cot_pytak_sync(
                            st.session_state.server_ip, 
                            st.session_state.server_port, 
                            report_type,  # Pass report type
                            st.session_state.report_data,  # Pass actual data
                            st.session_state.connection_type
                        ):
                            # Show success message
                            st.success(f"Report sent successfully via {st.session_state.connection_type}!")
                            report_status = "Sent"

                            # Show the formatted report
                            with st.expander("Sent Report Details"):
                                st.text(formatted_report)
                        else:
                            st.error(f"Failed to send report to TAK server at {st.session_state.server_ip}:{st.session_state.server_port}")
                            report_status = "Failed"
                        
                        # Save to history
                        save_report_to_history(report_type, st.session_state.report_data, ["Headquarters"], report_status)
                        
                        # Reset for new recording
                        st.session_state.audio_data = None
                        st.session_state.transcript = ""
                        st.session_state.report_data = {}
                        st.session_state.detected_report_type = None
                        
                        # Rerun to refresh UI
                        st.rerun()

    # History toggle at the bottom
    st.markdown("---")
    if st.button("Toggle Report History", use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history

    if st.button("Reset audio", use_container_width=True):
        st.session_state.audio_data = None
        st.session_state.transcript = ""
        st.session_state.report_data = {}
        st.session_state.detected_report_type = None
    
    # Show history if toggled on
    if st.session_state.show_history and st.session_state.report_history:
        st.markdown("### Report History")
        
        for i, report in enumerate(st.session_state.report_history):
            with st.expander(f"{report['title']} - {report['timestamp']}"):
                st.write(f"**Status:** {report['status']}")
                for field_id, value in report['data'].items():
                    # Find the field label from templates
                    field_label = next((field['label'] for field in report_templates[report['type']]['fields'] 
                                       if field['id'] == field_id), field_id)
                    st.write(f"**{field_label}:** {value}")

# Run the main app
if __name__ == "__main__":
    main()