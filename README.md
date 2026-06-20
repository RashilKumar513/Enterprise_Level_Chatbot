# Enterprise Level Chatbot - DocumentBrain 🧠

An intelligent, enterprise-grade document chatbot powered by advanced language models and vector database technology. This application enables users to upload documents, extract knowledge, and have natural conversations with an AI assistant that understands and grounds its responses in your document repository.

## 🌟 Features

- **Document Upload & Processing**: Upload multiple document types (PDF, DOCX, images with OCR)
- **Vector Database**: Efficient semantic search using ChromaDB
- **Intelligent Retrieval**: RAG (Retrieval-Augmented Generation) powered responses
- **Chat History Management**: Persistent chat sessions with conversation history
- **Authentication**: Secure login with credential verification
- **Multi-Service Architecture**: Separated chatbot and uploader services for scalability
- **Real-time Updates**: Automatic refresh of indexed documents
- **Source Attribution**: Transparent source document references for all responses

## 🏗️ Architecture

```
Enterprise Level Chatbot
├── chatbot_service/          # Streamlit-based chat interface
│   ├── app.py               # Main application entry point
│   ├── chat_store.py        # Chat session management
│   ├── llm.py              # LLM integration and prompting
│   ├── retriever.py        # Document retrieval logic
│   ├── query_handler.py    # Query processing and routing
│   ├── grounding.py        # Response grounding and validation
│   └── __init__.py
├── uploader_service/         # FastAPI backend for uploads
│   ├── main.py             # FastAPI application
│   ├── upload_page.py      # Web UI for uploads
│   ├── ingest.py           # Document ingestion pipeline
│   ├── processor.py        # Document processing
│   ├── chunker.py          # Text chunking strategies
│   ├── delete.py           # Document deletion
│   ├── auth_deps.py        # Authentication dependencies
│   └── __init__.py
├── shared/                   # Shared utilities
│   ├── config.py           # Configuration management
│   ├── database.py         # Database operations
│   ├── chat_db.py          # Chat-specific DB operations
│   ├── auth.py             # Authentication utilities
│   ├── chroma_manager.py   # Chroma DB management
│   ├── embedder.py         # Embedding generation
│   └── __init__.py
├── database/               # Data storage
│   └── chroma_db/         # Vector database storage
├── requirements.txt        # Python dependencies
├── run_chatbot.bat        # Windows batch script for chatbot
├── run_uploader.bat       # Windows batch script for uploader
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/RashilKumar513/Enterprise_Level_Chatbot.git
   cd Enterprise_Level_Chatbot
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**
   - Update `shared/config.py` with your settings (database paths, LLM models, etc.)
   - Set up environment variables if needed

### Running the Application

#### Option 1: Using Batch Scripts (Windows)

```bash
# Terminal 1 - Start the uploader service
run_uploader.bat

# Terminal 2 - Start the chatbot interface
run_chatbot.bat
```

#### Option 2: Manual Setup

```bash
# Terminal 1 - Start the FastAPI uploader service
cd uploader_service
uvicorn main:app --reload --port 8000

# Terminal 2 - Start the Streamlit chatbot app
cd chatbot_service
streamlit run app.py
```

## 📝 Usage

### Uploading Documents

1. Navigate to the upload interface (typically `http://localhost:8000`)
2. Log in with your credentials
3. Click "Upload Documents"
4. Select documents (PDF, DOCX, images)
5. Click "Upload" to process and index

### Chatting with DocumentBrain

1. Open the chatbot interface (typically `http://localhost:8501`)
2. Log in with your credentials
3. Type your questions about the uploaded documents
4. The AI will retrieve relevant content and provide grounded responses
5. Each response includes source document references

## 🔧 Technology Stack

### Backend & Core
- **FastAPI**: Modern web framework for the upload service
- **Streamlit**: Rapid prototyping framework for the chat interface
- **ChromaDB**: Vector database for embeddings and semantic search
- **Ollama**: Local LLM integration and inference

### NLP & Embeddings
- **Sentence-Transformers**: State-of-the-art embeddings generation
- **PyTesseract**: OCR for image-based documents

### Document Processing
- **PyPDF**: PDF reading and extraction
- **Python-docx**: Word document processing
- **Pillow**: Image processing

### Utilities
- **Pydantic**: Data validation
- **Requests**: HTTP client for API calls
- **NumPy**: Numerical computing

## 📦 Dependencies

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
streamlit>=1.32.0
chromadb>=0.5.0
sentence-transformers>=2.6.0
pypdf>=4.0.0
python-docx>=1.1.0
pytesseract>=0.3.10
pillow>=10.0.0
ollama>=0.1.9
pydantic>=2.0.0
python-multipart>=0.0.9
numpy>=1.26.0
requests>=2.31.0
```

## 🔐 Security

- **Authentication**: Username/password verification for access control
- **Admin Permissions**: Role-based access for document management
- **Session Management**: Secure session handling with chat isolation

## 📊 Project Structure Details

### Chat Service (`chatbot_service/`)
- Handles user interactions through Streamlit UI
- Manages chat history and context
- Integrates with LLM for response generation
- Performs retrieval from vector database

### Uploader Service (`uploader_service/`)
- REST API for document uploads
- Document processing pipeline
- Embedding generation and indexing
- Document deletion and management

### Shared Utilities (`shared/`)
- Centralized configuration
- Database access layer
- Authentication logic
- ChromaDB management
- Embedding generation

## 🎯 Key Features Explained

### Retrieval-Augmented Generation (RAG)
The chatbot retrieves relevant documents based on user queries and uses them to ground its responses, ensuring accuracy and traceability.

### Multi-Service Architecture
Separation of concerns with dedicated services for:
- User interaction (Streamlit)
- Document management (FastAPI)
- Shared utilities and infrastructure

### Persistent Storage
- Chat history stored in database
- Document embeddings persisted in ChromaDB
- User session management

## 🔄 Workflow

1. **Document Upload** → Processing → Chunking → Embedding → Storage
2. **User Query** → Embedding → Retrieval → LLM Processing → Response
3. **Response** → Source Attribution → Display → History Persistence

## 🐛 Troubleshooting

### Services Won't Start
- Ensure Python 3.8+ is installed
- Check all dependencies: `pip install -r requirements.txt`
- Verify ports 8000 (uploader) and 8501 (chatbot) are available

### Document Upload Issues
- Check file format compatibility (PDF, DOCX, images)
- Verify file size limits
- Ensure ChromaDB is accessible

### Embedding Generation Issues
- Verify Ollama is running (if using local models)
- Check sentence-transformers installation
- Review GPU availability if CUDA enabled

## 📚 API Endpoints

### Upload Service (`/api/...`)
- `POST /auth/login` - User authentication
- `GET /auth/verify` - Session verification
- `POST /documents/upload` - Upload and process documents
- `GET /documents` - List all documents
- `DELETE /documents/{doc_id}` - Remove a document

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is provided as-is for educational and enterprise use.

## 👤 Author

**Rashil Kumar**

- GitHub: [@RashilKumar513](https://github.com/RashilKumar513)
- Project: [Enterprise_Level_Chatbot](https://github.com/RashilKumar513/Enterprise_Level_Chatbot)

## 🙏 Acknowledgments

- Built with FastAPI, Streamlit, and ChromaDB
- Leverages Ollama for local LLM inference
- Uses Sentence-Transformers for embeddings

## 📞 Support

For issues, questions, or suggestions, please open an issue on the GitHub repository.

---

**Last Updated**: 2026-06-20

Made with ❤️ for enterprise AI solutions
