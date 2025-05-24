Military Report Automation MVP

A Streamlit-based MVP for automated military reporting using speech recognition with advanced AI integration.
Project Structure

military-comms-mvp/
├── app/
│   ├── main.py                # Main Streamlit application
│   ├── models/                # AI model integrations
│   │   ├── whisper.py         # Whisper speech-to-text model
│   │   ├── qwen.py            # Qwen NLP model
│   │   └── __init__.py        # Make models a proper package
│   ├── utils/                 # Utility functions
│   │   ├── audio.py           # Audio processing utilities
│   │   ├── reports.py         # Report template processing
│   │   ├── ai.py              # AI integration coordination
│   │   ├── military.py        # Military-specific utilities
│   │   └── __init__.py        # Make utils a proper package
│   └── templates/             # Report templates (JSON)
├── scripts/
│   └── setup_models.py        # Script to set up AI models
├── docs/
│   ├── deployment_guide.md    # Deployment instructions
│   └── ai_model_integration.md # AI model setup guide
├── tests/                     # Test directory
├── .streamlit/               # Streamlit configuration
├── .env                      # Environment variables & configuration
├── requirements.txt          # Dependencies
└── README.md                 # Documentation

Features

    Speech-to-text conversion for military reports using Whisper AI
    Support for multiple report templates (CONTACTREP, SITREP, MEDEVAC, RECCEREP)
    Automated field extraction from natural language using Qwen AI
    Multi-language support for international operations
    Report editing and validation
    Simulated transmission to appropriate recipients
    Intelligent priority suggestion

Technologies Used

    Streamlit: For the web interface
    Whisper: For speech recognition (OpenAI's open-source speech-to-text model)
    Qwen: For NLP and entity extraction from transcripts
    Python: Backend language for AI model integration
    PyTorch: Deep learning framework for AI models

Getting Started
Basic Setup (No AI Models)

    Clone the repository:

    git clone <repository-url>
    cd military-comms-mvp

    Install requirements:

    pip install -r requirements.txt

    Run the Streamlit app with mock AI (no models required):

    streamlit run app/main.py -- --mock

Full Setup with AI Models

Follow these steps to set up the full application with AI models:

    Install requirements:

    pip install -r requirements.txt

    Set up AI models (automatic download):

    python scripts/setup_models.py --quick

    This will download the smaller versions of Whisper and Qwen models for a balanced experience.
    Run the Streamlit app:

    streamlit run app/main.py

For detailed AI setup instructions, see docs/ai_model_integration.md.
Using the Application

    Select Report Type: Choose the type of report you want to create (CONTACTREP, SITREP, etc.)
    Record Report: Speak your report clearly into the microphone
    Review & Edit: The AI will extract fields automatically; review and edit as needed
    Send Report: Select recipients and send the formatted report

Development Roadmap
Phase 1: Core MVP (Completed)

    Basic UI with report templates
    Mock speech-to-text functionality
    Mock NLP for field extraction
    Simulated transmission

Phase 2: AI Integration (Completed)

    ✅ Integrate Whisper for speech recognition
    ✅ Integrate Qwen for NLP and field extraction
    ✅ Support for multiple languages

Phase 3: Production Features

    User authentication
    Secure transmission
    Offline support
    Mobile optimization

System Requirements

For running with AI models:

    Python 3.8+
    8GB RAM (16GB recommended)
    5GB free disk space
    CUDA-compatible GPU recommended (not required)

For development/testing with mock AI:

    Python 3.8+
    4GB RAM
    1GB free disk space

Troubleshooting

If you encounter issues with the AI models:

    Try running in mock mode to test functionality:

    streamlit run app/main.py -- --mock

    Check if your microphone is working properly in your browser
    See docs/ai_model_integration.md for detailed troubleshooting


