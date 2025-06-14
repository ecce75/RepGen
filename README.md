# RepGen - Voice-Enabled Military Reporting for TAK

A Streamlit-based application for automated military reporting using speech recognition with advanced AI integration. Reports are exported as TAK (Team Awareness Kit) Cursor-on-Target (CoT) XML files for seamless integration with WinTAK and other TAK systems.

## Project Structure

```
repgen/
├── app/
│   ├── main.py                # Main Streamlit application
│   ├── models/                # AI model integrations
│   │   ├── whisper.py         # Whisper speech-to-text model
│   │   ├── qwen.py            # Qwen NLP model
│   │   └── __init__.py        
│   ├── utils/                 # Utility functions
│   │   ├── audio.py           # Audio processing utilities
│   │   ├── reports.py         # Report template processing
│   │   ├── ai.py              # AI integration coordination
│   │   ├── military.py        # Military-specific utilities
│   │   ├── cot_xml.py         # TAK CoT XML generation
│   │   └── __init__.py        
│   └── data/                  # Report templates and data
├── .streamlit/               # Streamlit configuration
├── .env                      # Environment variables & configuration
├── requirements.txt          # Dependencies
├── environment.yml           # Conda environment
├── README.md                 # This file
└── INSTALLATION.md           # Installation guide
```

## Features

- **Speech-to-text conversion** for military reports using Whisper AI
- **Support for multiple report templates** (CONTACTREP, SITREP, MEDEVAC, SPOTREP, SALUTE, PATROLREP)
- **Automated field extraction** from natural language using Qwen AI
- **TAK CoT XML export** - Reports are automatically exported as Cursor-on-Target XML files for WinTAK import
- **NATO-standard report formats** aligned with military communication standards
- **Report editing and validation** with required field checking
- **Real-time transcription** with audio playback controls
- **Report history** tracking for session management

## Technologies Used

- **Streamlit**: Web interface framework
- **Whisper**: Speech recognition (OpenAI's open-source speech-to-text model)
- **Qwen**: NLP and entity extraction from transcripts
- **Python**: Backend language for AI model integration
- **PyTorch**: Deep learning framework for AI models
- **XML**: TAK Cursor-on-Target format for military interoperability

## Getting Started

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd repgen
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or using conda:
   ```bash
   conda env create -f environment.yml
   conda activate repgen
   ```

3. **Run the application:**
   ```bash
   streamlit run app/main.py
   ```

For detailed installation instructions including platform-specific setup, see [INSTALLATION.md](INSTALLATION.md).
## Using the Application

1. **Record Report**: Click the record button and speak your report clearly
2. **Process Recording**: Click "Process Recording" to transcribe and analyze
3. **Review & Edit**: The AI will extract fields automatically; review and edit as needed
4. **Send Report**: Click "Send Report" to generate the TAK CoT XML file

### TAK Integration

When you send a report, RepGen automatically generates a TAK Cursor-on-Target XML file that can be imported into WinTAK or other TAK systems. The XML file is saved to your configured TAK import directory (default: `~/TAK/import`).

## Development Status

### ✅ Completed Features

- Speech-to-text with Whisper AI
- NLP field extraction with Qwen AI
- NATO-standard report templates
- TAK CoT XML export for WinTAK integration
- Real-time transcription and editing
- Report validation and history

### 🚧 Future Enhancements

- Enhanced coordinate parsing (MGRS to decimal degrees)
- Additional report templates
- Secure transmission capabilities
- Mobile optimization
- Multi-language support

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

## Configuration

### TAK Integration Setup

By default, TAK CoT XML files are saved to `~/TAK/import`. You can configure this by setting the `WINTAK_IMPORT_DIR` environment variable:

```bash
export WINTAK_IMPORT_DIR="/path/to/your/tak/import"
```

## Troubleshooting

- **Microphone not working**: Ensure your browser has microphone permissions
- **Model loading issues**: Check internet connection and available disk space
- **TAK XML not importing**: Verify the WinTAK import directory path is correct
- **Performance issues**: Consider using smaller model sizes (see INSTALLATION.md)

For detailed troubleshooting, see [INSTALLATION.md](INSTALLATION.md).


