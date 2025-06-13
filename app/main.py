import streamlit as st
import time
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.ai import process_speech_to_text, determine_report_type_from_transcript, extract_entities_from_text
from app.utils.reports import load_report_templates, save_report_to_history, format_report_for_transmission
from app.utils.audio import get_audio_from_microphone

# Set page configuration
st.set_page_config(
    page_title="RepGen",
    page_icon="🔊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state variables if they don't exist
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

# Load report templates
report_templates = load_report_templates()

def main():
    # Simple header
    st.title("RepGen - Voice-Enabled Military Reporting for TAK")
    
    # Create a two-column layout for the main interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
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
                        # Process speech to text
                        transcript = process_speech_to_text(st.session_state.audio_data)
                        st.session_state.transcript = transcript
                        
                        # Notify user that transcription is complete
                        st.success("Transcription complete! See below for results.")
                    
                    with st.spinner("Analyzing report type..."):
                        # Basic report type detection (simplified without Qwen)
                        report_type, confidence = determine_report_type_from_transcript(transcript)
                        st.session_state.detected_report_type = report_type
                        st.session_state.detection_confidence = confidence
                    
                    with st.spinner("Preparing report template..."):
                        # Just get empty fields (Qwen disabled)
                        st.session_state.report_data = extract_entities_from_text(
                            report_type,
                            transcript
                        )
        
        # Display the transcript if available with more prominence
        if st.session_state.transcript:
            st.markdown("### Transcript")
            # Use a container with a border to make transcript stand out
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
                
                st.markdown(f"<div class='transcript-box'>{st.session_state.transcript}</div>", unsafe_allow_html=True)
                
                # Add a button to copy transcript to clipboard (using JS)
                st.markdown("""
                <script>
                function copyTranscript() {
                    const transcript = document.querySelector('.transcript-box').innerText;
                    navigator.clipboard.writeText(transcript)
                        .then(() => alert('Transcript copied to clipboard!'))
                        .catch(err => console.error('Could not copy text: ', err));
                }
                </script>
                <button onclick="copyTranscript()">Copy Transcript</button>
                """, unsafe_allow_html=True)
    
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
                        time.sleep(1.5)
                        
                        # Format the report for display
                        formatted_report = format_report_for_transmission(report_type, st.session_state.report_data)
                        
                        # Save to history
                        save_report_to_history(report_type, st.session_state.report_data, ["Headquarters"], "Sent")
                        
                        # Display success message
                        st.success("Report sent successfully!")
                        
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