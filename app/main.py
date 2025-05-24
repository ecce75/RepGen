import streamlit as st
import time
import json
import pandas as pd
from datetime import datetime
import base64
import io
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.ai import process_speech_to_text, determine_report_type_from_transcript, extract_entities_from_text
from app.utils.reports import load_report_templates, save_report_to_history
from app.utils.audio import get_audio_from_microphone

# Set page configuration
st.set_page_config(
    page_title="RepGen",
    page_icon="🔊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Application title and introduction
st.title("Military Report Automation System")
st.markdown("""
This system allows rapid creation of standardized military reports using speech recognition.
You can either:
- **Quick Record**: Speak your report directly and let the AI determine the report type
- **Select Report Type**: Choose a report type first, then record your report

In both cases, the system will automatically fill the form fields based on your spoken report.
""")

# Initialize session state variables if they don't exist
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'report_data' not in st.session_state:
    st.session_state.report_data = {}
if 'report_history' not in st.session_state:
    st.session_state.report_history = []
if 'step' not in st.session_state:
    st.session_state.step = 1  # 1: Select report, 2: Record, 3: Edit, 4: Send
if 'detected_report_type' not in st.session_state:
    st.session_state.detected_report_type = None
if 'detection_confidence' not in st.session_state:
    st.session_state.detection_confidence = 0
if 'use_auto_detection' not in st.session_state:
    st.session_state.use_auto_detection = False

# Load report templates
report_templates = load_report_templates()


def determine_recipients(report_type):
    """Determine appropriate recipients based on report type"""
    from app.utils.ai import suggest_additional_recipients

    # Get suggested recipients from the AI
    if st.session_state.report_data:
        return suggest_additional_recipients(report_type, st.session_state.report_data)

    # Fallback to defaults if no report data yet
    recipients = {
        "CONTACTREP": ["Battalion TOC", "Company CP", "Adjacent Units"],
        "SITREP": ["Battalion S3", "Company Commander"],
        "MEDEVAC": ["Battalion Aid Station", "MEDEVAC Dispatch", "Company CP"],
        "RECCEREP": ["Battalion S2", "Company CP"]
    }
    return recipients.get(report_type, ["Chain of Command"])


def handle_recording_in_step_1():
    """
    Handle the recording flow in Step 1 (Quick Record).
    This improves the UX when dealing with microphone permissions.
    """
    # Display recording UI
    st.markdown("""
    ### Quick Record
    Record your report directly and let the AI determine the report type.
    Speak clearly and include the report type in your recording (e.g., "Contact Report", "Situation Report").
    """)

    # Single record button for auto-detection
    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.audio_data = get_audio_from_microphone(key="quick_record_microphone")

    # Only show the continue button when we have audio data
    if st.session_state.audio_data:
        with col2:
            if st.button("Process Recording", key="process_quick_record"):
                with st.spinner("Processing your recording..."):
                    # Process the audio to text
                    transcript = process_speech_to_text(st.session_state.audio_data)
                    st.session_state.transcript = transcript

                    # Display the transcript
                    st.subheader("Transcript:")
                    st.write(st.session_state.transcript)

                    # Determine report type from transcript
                    report_type, confidence = determine_report_type_from_transcript(transcript)
                    st.session_state.detected_report_type = report_type
                    st.session_state.detection_confidence = confidence

                    # Ask user to confirm or change report type
                    st.session_state.use_auto_detection = True
                    st.session_state.selected_report_type = report_type

                    # Extract form data from transcript
                    with st.spinner("Extracting information from your report..."):
                        st.session_state.report_data = extract_entities_from_text(
                            report_type,
                            st.session_state.transcript
                        )

                    # Move to review step
                    st.session_state.step = 3
                    st.rerun()

        # Show a preview of the recorded audio
        st.audio(st.session_state.audio_data, format="audio/wav")
        st.markdown("**Preview your recording above. Click 'Process Recording' when ready.**")


def handle_recording_in_step_2():
    """
    Handle the recording flow in Step 2 (Manual Report Type).
    This improves the UX when dealing with microphone permissions.
    """
    # Brief instructions
    st.markdown(f"""
    Record your {report_templates[st.session_state.selected_report_type]['title']} using the microphone.
    Speak clearly and include all relevant information.

    **Example format:**
    ```
    {report_templates[st.session_state.selected_report_type]['title']}. 
    [Unit]. [Location]. [Key information relevant to this report type]...
    ```
    """)

    # Audio recording in main column, process button in side column
    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.audio_data = get_audio_from_microphone(key="manual_type_record")

    # Only show continue button when we have audio
    if st.session_state.audio_data:
        with col2:
            if st.button("Process Recording", key="process_manual_record"):
                with st.spinner("Processing your recording..."):
                    # Process the audio to text
                    transcript = process_speech_to_text(st.session_state.audio_data)
                    st.session_state.transcript = transcript

                    # Display the transcript
                    st.subheader("Transcript:")
                    st.write(st.session_state.transcript)

                    # Extract form data from transcript
                    with st.spinner("Extracting information from your report..."):
                        st.session_state.report_data = extract_entities_from_text(
                            st.session_state.selected_report_type,
                            st.session_state.transcript
                        )

                    # Move to review step
                    st.session_state.step = 3
                    st.rerun()

        # Show a preview of the recorded audio
        st.audio(st.session_state.audio_data, format="audio/wav")
        st.markdown("**Preview your recording above. Click 'Process Recording' when ready.**")

    # Option to go back
    if st.button("Back to Report Selection"):
        st.session_state.step = 1
        st.rerun()

# Main application flow
def main():
    # Sidebar with steps
    with st.sidebar:
        st.header("Process Steps")

        # Adjust step display based on whether auto-detection was used
        if st.session_state.use_auto_detection:
            # For auto-detection flow
            st.markdown(f"{'✅' if st.session_state.step >= 1 else '1️⃣'} **Quick Record & Auto-detect**")
            st.markdown(f"{'✅' if st.session_state.step >= 3 else '2️⃣'} **Review & Edit**")
            st.markdown(f"{'✅' if st.session_state.step >= 4 else '3️⃣'} **Send Report**")
        else:
            # For manual selection flow
            st.markdown(f"{'✅' if st.session_state.step >= 1 else '1️⃣'} **Select Report Type**")
            st.markdown(f"{'✅' if st.session_state.step >= 2 else '2️⃣'} **Record Report**")
            st.markdown(f"{'✅' if st.session_state.step >= 3 else '3️⃣'} **Review & Edit**")
            st.markdown(f"{'✅' if st.session_state.step >= 4 else '4️⃣'} **Send Report**")

        st.markdown("---")

        # Report history in sidebar
        st.header("Report History")
        if st.session_state.report_history:
            for i, report in enumerate(st.session_state.report_history):
                with st.expander(f"{report['title']} - {report['timestamp']}"):
                    st.write(f"**Status:** {report['status']}")
                    for field_id, value in report['data'].items():
                        # Find the field label from templates
                        field_label = next((field['label'] for field in report_templates[report['type']]['fields']
                                            if field['id'] == field_id), field_id)
                        st.write(f"**{field_label}:** {value}")
        else:
            st.write("No reports yet.")

    # Main content area
    if st.session_state.step == 1:
        # Step 1: Select report type or use auto-detection
        st.header("Step 1: Create Report")

        # Add tabs for different report creation methods
        tab1, tab2 = st.tabs(["Quick Record", "Select Report Type"])

        with tab1:
            handle_recording_in_step_1()

        with tab2:
            st.markdown("### Select Report Type")
            # Display report type selection as cards in columns
            cols = st.columns(len(report_templates))
            for i, (report_id, report_info) in enumerate(report_templates.items()):
                with cols[i]:
                    st.subheader(report_info["title"])
                    st.write(report_info["description"])
                    if st.button(f"Select {report_info['title']}", key=f"btn_{report_id}"):
                        st.session_state.selected_report_type = report_id
                        st.session_state.use_auto_detection = False
                        st.session_state.step = 2
                        st.rerun()


    elif st.session_state.step == 2:

        # Step 2: Record speech

        st.header(f"Step 2: Record {report_templates[st.session_state.selected_report_type]['title']}")

        # Use our new improved handler function

        handle_recording_in_step_2()

    elif st.session_state.step == 3:
        # Step 3: Review and edit form data
        st.header(f"Step 3: Review and Edit {report_templates[st.session_state.selected_report_type]['title']}")

        # Show the transcript
        with st.expander("Show Transcript"):
            st.write(st.session_state.transcript)

        # If report type was auto-detected, allow user to change it
        if st.session_state.use_auto_detection:
            st.info(
                f"AI detected report type: **{report_templates[st.session_state.selected_report_type]['title']}** (Confidence: {st.session_state.detection_confidence:.2f})")

            # Allow user to change report type if needed
            st.write("If this is incorrect, please select the correct report type:")
            cols = st.columns(len(report_templates))
            for i, (report_id, report_info) in enumerate(report_templates.items()):
                with cols[i]:
                    if st.button(f"Change to {report_info['title']}", key=f"change_to_{report_id}",
                                 disabled=(report_id == st.session_state.selected_report_type)):
                        # Update report type and re-extract fields
                        st.session_state.selected_report_type = report_id

                        # Re-extract form data for the new report type
                        st.session_state.report_data = extract_entities_from_text(
                            report_id,
                            st.session_state.transcript
                        )
                        st.rerun()

        # Create a form for editing
        with st.form("edit_report_form"):
            # Display and allow editing of each field
            report_type = st.session_state.selected_report_type
            template = report_templates[report_type]

            for field in template["fields"]:
                field_id = field["id"]
                field_label = field["label"]
                required = field["required"]
                placeholder = field.get("placeholder", "")

                # Get the current value
                current_value = st.session_state.report_data.get(field_id, "")

                # Create the input field
                new_value = st.text_input(
                    f"{field_label}{' *' if required else ''}",
                    value=current_value,
                    placeholder=placeholder,
                    key=f"input_{field_id}"
                )

                # Update the report data
                st.session_state.report_data[field_id] = new_value

            # Form submission buttons
            col1, col2 = st.columns(2)
            with col1:
                back_button = st.form_submit_button("Back to Recording")
            with col2:
                submit_button = st.form_submit_button("Continue to Send")

        if back_button:
            st.session_state.step = 2
            st.rerun()

        if submit_button:
            # Validate that required fields are filled
            report_type = st.session_state.selected_report_type
            template = report_templates[report_type]
            required_fields = [field["id"] for field in template["fields"] if field["required"]]

            missing_fields = []
            for field_id in required_fields:
                if not st.session_state.report_data.get(field_id):
                    missing_fields.append(field_id)

            if missing_fields:
                # Show error for missing fields
                st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
            else:
                st.session_state.step = 4
                st.rerun()

    elif st.session_state.step == 4:
        # Step 4: Send report
        st.header(f"Step 4: Send {report_templates[st.session_state.selected_report_type]['title']}")

        # Display the final report
        st.subheader("Report Summary")
        report_type = st.session_state.selected_report_type
        template = report_templates[report_type]

        # Format report data as a table
        report_data = []
        for field in template["fields"]:
            field_id = field["id"]
            field_label = field["label"]
            value = st.session_state.report_data.get(field_id, "")
            report_data.append({"Field": field_label, "Value": value})

        report_df = pd.DataFrame(report_data)
        st.table(report_df)

        # Recipients selection
        st.subheader("Select Recipients")
        recipients = determine_recipients(report_type)
        selected_recipients = []

        cols = st.columns(len(recipients))
        for i, recipient in enumerate(recipients):
            with cols[i]:
                if st.checkbox(recipient, value=True, key=f"recipient_{i}"):
                    selected_recipients.append(recipient)

        # Transmission options
        st.subheader("Transmission Options")

        from app.utils.ai import analyze_report_priority
        # Get suggested priority from AI
        suggested_priority = analyze_report_priority(report_type, st.session_state.report_data)

        priority = st.select_slider(
            "Priority",
            options=["Routine", "Priority", "Immediate", "Flash"],
            value=suggested_priority
        )

        encryption = st.checkbox("Use Encryption", value=True)
        confirmation = st.checkbox("Request Read Receipt", value=False)

        # Send button
        if st.button("Send Report"):
            with st.spinner("Sending report..."):
                # In a real implementation, this would actually send the report
                # For now, we just simulate sending
                time.sleep(2)

                # Save to history
                save_report_to_history(report_type, st.session_state.report_data, selected_recipients, status="Sent")

                # Show success message
                st.success(f"""
                Report sent successfully!
                - Type: {template['title']}
                - Recipients: {', '.join(selected_recipients)}
                - Priority: {priority}
                - Encryption: {'Enabled' if encryption else 'Disabled'}
                - Read Receipt: {'Requested' if confirmation else 'Not Requested'}
                """)

                # Reset to start
                if st.button("Start New Report"):
                    st.session_state.step = 1
                    st.session_state.audio_data = None
                    st.session_state.transcript = ""
                    st.session_state.report_data = {}
                    st.session_state.detected_report_type = None
                    st.session_state.detection_confidence = 0
                    st.session_state.use_auto_detection = False
                    st.rerun()


# Run the main app
if __name__ == "__main__":
    main()