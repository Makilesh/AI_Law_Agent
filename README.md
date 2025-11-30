# ⚖️ AI Legal Engine

> **An intelligent RAG-powered legal assistant for Indian law with multilingual support and document processing**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Google Gemini](https://img.shields.io/badge/Gemini-2.5--flash-orange.svg)](https://ai.google.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-local-green.svg)](https://www.trychroma.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 What is This?

AI Legal Engine is a **free, local-first RAG system** for Indian criminal law. Ask legal questions in English, Hindi, or Tamil and get accurate answers powered by **Google Gemini 2.5 Flash** with document retrieval from your own knowledge base.

**Live Demo**: Chat with seeded database containing IPC sections & Motor Vehicles Act penalties!

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Smart RAG** | Retrieves from ChromaDB vector store, falls back to Gemini's knowledge |
| 🆓 **100% Free** | Google Gemini (free tier) + ChromaDB (local) + Sentence Transformers (local) |
| 📄 **PDF Upload** | Upload legal documents and chat with them instantly |
| 🌐 **Multilingual** | English, हिन्दी (Hindi), தமிழ் (Tamil) |
| ⚡ **Fast Setup** | 5-minute installation with automatic database seeding |
| 🎨 **Modern UI** | Beautiful gradient interface with real-time responses |

---

## 🚀 Quick Start

### 1️⃣ Install Dependencies
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 2️⃣ Configure API Key
```bash
# Create .env file
echo GEMINI_API_KEY=your_api_key_here > .env
```

**Get your free API key**: https://ai.google.dev/

### 3️⃣ Seed Database (Optional)
```bash
# Populate with IPC sections & traffic laws
python seed_database.py
```

### 4️⃣ Start Server
```bash
# Backend API
python main.py

# Frontend (in new terminal)
python -m http.server 3000 --directory frontend
```

**Open**: http://localhost:3000 🎉

---

## 💬 Usage Examples

### Ask Legal Questions
```
Q: "What is IPC 420?"
A: Detailed explanation with penalties, examples, and legal provisions

Q: "What happens if I get fined 10000 for not wearing a helmet?"
A: Retrieves Motor Vehicles Act penalties from database + Gemini analysis

Q: "मुझे जमानत कैसे मिलेगी?" (Hindi)
A: Bail process explanation in Hindi
```

### Upload Documents
- Drag & drop PDF files
- System automatically chunks and indexes them
- Ask questions about your uploaded documents

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│          FastAPI Server (Port 8000)             │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    ┌────▼────┐         ┌───▼─────┐
    │  Chat   │         │  Upload │
    │  /chat  │         │  /upload│
    └────┬────┘         └────┬────┘
         │                   │
         └────────┬──────────┘
                  │
         ┌────────▼─────────┐
         │  Router Agent    │
         │  (Query Routing) │
         └────────┬─────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼────┐  ┌─────▼──────┐  ┌──▼─────┐
│Classify│  │Section     │  │  PDF   │
│Agent   │  │Expert Agent│  │Processor│
└────────┘  └─────┬──────┘  └────────┘
                  │
         ┌────────▼─────────┐
         │  ChromaDB Store  │
         │  (23 seed docs)  │
         └──────────────────┘
                  │
         ┌────────▼─────────┐
         │ Sentence Trans.  │
         │ (MiniLM-L6-v2)  │
         └──────────────────┘
                  │
         ┌────────▼─────────┐
         │  Gemini 2.5      │
         │  Flash (Free)    │
         └──────────────────┘
```

---

## 📁 Project Structure

```
AI_Law_Agent/
├── 🎯 main.py                  # FastAPI server & endpoints
├── 🤖 agents/
│   ├── legal_classifier.py    # Classify legal queries
│   ├── section_expert.py      # Explain IPC/laws
│   ├── router.py              # Route to best agent
│   └── pdf_processor.py       # Process PDFs
├── 🔧 utils/
│   ├── gemini_agent.py        # Gemini wrapper
│   ├── vector_store.py        # ChromaDB operations
│   └── prompts.py             # System instructions
├── 🎨 frontend/
│   ├── index.html             # Chat interface
│   ├── styles.css             # Gradient design
│   └── script.js              # API interactions
├── 📚 seed_data/
│   ├── traffic_laws.txt       # Motor Vehicles Act
│   └── common_ipc_sections.txt# IPC sections
├── 📦 seed_database.py        # One-time DB setup
└── 🔐 .env                    # API keys (not committed)
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Google Gemini 2.5 Flash | Free, fast generation |
| **Vector DB** | ChromaDB | Local persistent storage |
| **Embeddings** | Sentence Transformers | Free local embeddings |
| **Backend** | FastAPI | REST API framework |
| **Frontend** | Vanilla JS | Lightweight UI |
| **PDF Processing** | LangChain + PyPDF | Document chunking |

**Total Cost**: $0/month 💰

---

## 📊 API Endpoints

### Chat
```bash
POST /chat
Content-Type: application/json

{
  "query": "What is IPC 420?",
  "language": "English"
}

Response:
{
  "response": "Section 420 - Cheating...",
  "confidence": 0.95,
  "source": "gemini-2.5-flash",
  "language": "English"
}
```

### Upload PDF
```bash
POST /upload-pdf
Content-Type: multipart/form-data

file: document.pdf

Response:
{
  "success": true,
  "filename": "document.pdf",
  "pages_processed": 10,
  "chunks_created": 45
}
```

### Health Check
```bash
GET /health

Response:
{
  "status": "healthy",
  "gemini_configured": true,
  "vector_store": {
    "total_documents": 23,
    "collection_name": "legal_documents"
  }
}
```

### Vector Store Stats
```bash
GET /vector-store/stats

Response:
{
  "total_documents": 23,
  "collection_name": "legal_documents"
}
```

---

## 🧪 Testing

```bash
# Test IPC query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What is IPC 420?","language":"English"}'

# Test traffic law query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"helmet fine penalty","language":"English"}'

# Upload document
curl -X POST http://localhost:8000/upload-pdf \
  -F "file=@legal_doc.pdf"

# Check health
curl http://localhost:8000/health
```

---

## 🎓 How It Works

### Retrieval-Augmented Generation (RAG)

1. **Query Reception** → User asks a question
2. **Vector Search** → Sentence Transformers converts query to embedding
3. **ChromaDB Retrieval** → Finds top 5 most relevant document chunks
4. **Context Building** → Combines retrieved docs with query
5. **Gemini Generation** → Gemini 2.5 Flash generates answer using context
6. **Fallback** → If no good matches, uses Gemini's built-in knowledge

**Result**: Accurate answers grounded in your documents! 📚

---

## 🔐 Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (defaults shown)
CHROMA_PERSIST_DIR=./chroma_db
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=true
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `GEMINI_API_KEY not found` | Create `.env` file with your API key |
| `Model not found` | Ensure using `gemini-2.5-flash` (not 1.5) |
| `ChromaDB empty` | Run `python seed_database.py` |
| `Frontend not loading` | Check if server is on http://localhost:3000 |
| `CORS errors` | Backend runs on 8000, frontend on 3000 |

---

## 🚦 Commands Cheat Sheet

```bash
# Setup
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python seed_database.py

# Run
python main.py                              # Start backend
python -m http.server 3000 --directory frontend  # Start frontend

# Alternative startup scripts
start.bat                    # Auto-creates venv if needed
quick_start.bat             # Simple startup
.\venv\Scripts\activate && python main.py  # Manual
```

---

## 📈 Seeded Data

The database comes pre-loaded with:

| Category | Count | Content |
|----------|-------|---------|
| **IPC Sections** | 14 chunks | Sections 302, 304, 307, 376, 420, 498A, etc. |
| **Traffic Laws** | 9 chunks | Motor Vehicles Act penalties |
| **Total** | 23 docs | Ready to query! |

Add more with `python seed_database.py` or upload PDFs via UI.

---

## 🌟 Highlights

✅ **No Azure/OpenAI costs** - 100% free tier services  
✅ **No internet needed** - ChromaDB & embeddings run locally  
✅ **Privacy-first** - Your documents never leave your machine  
✅ **Production-ready** - FastAPI, error handling, CORS configured  
✅ **Extensible** - Add more agents, languages, or document types  

---

## 📝 License

MIT License - Free for personal and commercial use

---

## 🤝 Contributing

Found a bug? Want to add features?

1. Fork the repo
2. Create your feature branch
3. Submit a pull request

---

## 📚 Learn More

- [Google Gemini API](https://ai.google.dev/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [FastAPI Guide](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)

---

<div align="center">

**Built with ❤️ for Indian Legal Tech**

*Star ⭐ this repo if you found it helpful!*

</div>
