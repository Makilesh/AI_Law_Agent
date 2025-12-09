# Complete Setup Guide - AI Legal Engine (Free Tier)

## 📋 What We Built

A **fully functional agentic legal assistant** for Indian Criminal Law using **100% FREE services**:

- ✅ Google Gemini API (free tier)
- ✅ ChromaDB (local vector database)
- ✅ Sentence Transformers (local embeddings)
- ✅ FastAPI backend
- ✅ No Azure, No Pinecone, No paid subscriptions!

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         USER QUERY                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     ROUTER AGENT (Gemini)                   │
│  Analyzes query and routes to appropriate specialist        │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┬─────────────┐
         │             │             │             │
         ▼             ▼             ▼             ▼
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐
│ CLASSIFIER │  │  SECTION   │  │    PDF     │  │ GENERAL  │
│   AGENT    │  │   EXPERT   │  │ PROCESSOR  │  │ ASSISTANT│
│  (Gemini)  │  │  (Gemini)  │  │  (Gemini)  │  │ (Gemini) │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬─────┘
      │               │               │              │
      │               │               ▼              │
      │               │      ┌──────────────┐        │
      │               │      │  ChromaDB    │        │
      │               │      │  (Vector DB) │        │
      │               │      └──────────────┘        │
      │               │                              │
      └───────────────┴──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    MULTILINGUAL RESPONSE                    │
│         (English, Hindi, Telugu, Tamil, etc.)               │
└─────────────────────────────────────────────────────────────┘
```

## 📦 What's Included

### Core Files

1. **Agents** (`agents/`)
   - `legal_classifier.py` - Classifies queries (LAW_QUERY, SECTION_QUERY, etc.)
   - `section_expert.py` - Explains legal sections in detail
   - `router.py` - Routes queries to appropriate agents
   - `pdf_processor.py` - Processes and queries PDF documents

2. **Utilities** (`utils/`)
   - `gemini_agent.py` - Wrapper for Google Gemini API
   - `vector_store.py` - ChromaDB vector storage manager

3. **Models** (`models/`)
   - `schemas.py` - Pydantic models for requests/responses

4. **Main Application**
   - `main.py` - FastAPI server with all endpoints

5. **Configuration**
   - `.env` - Environment variables (with your Gemini key)
   - `requirements.txt` - All dependencies (FREE packages only)

6. **Utilities**
   - `start.bat` - Quick start script
   - `test_api.py` - Test suite

## 🔑 Key Features Implemented

### 1. Query Routing
- Automatic classification of user queries
- Routes to specialized agents based on intent

### 2. Legal Section Expert
- Detailed explanations of IPC, CrPC sections
- Penalties, examples, related sections
- Vector search for relevant legal context

### 3. PDF Processing
- Upload legal PDFs
- Automatic chunking and embedding
- Semantic search across documents
- Q&A based on document content

### 4. Multilingual Support
- Supports multiple Indian languages
- English, Hindi, Telugu, Tamil, Malayalam, etc.
- Language detection and response generation

### 5. Context-Aware
- Maintains conversation history
- Provides contextual responses

## 🚀 How to Use

### Step 1: Start the Server

```cmd
start.bat
```

OR

```cmd
python main.py
```

Server starts at: `http://localhost:8000`

### Step 2: Access API Documentation

Open browser: `http://localhost:8000/docs`

Interactive Swagger UI with all endpoints!

### Step 3: Test the API

Run the test suite:

```cmd
python test_api.py
```

### Step 4: Make Requests

#### Chat Example

```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "query": "What is IPC Section 420?",
    "language": "English"
})

print(response.json()["response"])
```

#### Upload PDF Example

```python
with open("legal_doc.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload-pdf",
        files={"file": f}
    )

print(response.json())
```

## 📊 All API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/chat` | POST | Chat with legal assistant |
| `/upload-pdf` | POST | Upload legal PDF |
| `/document-stats` | GET | Document statistics |
| `/clear-documents` | POST | Clear all documents |
| `/clear-history` | POST | Clear conversation history |

## 🔧 Configuration Options

### Environment Variables (`.env`)

```env
# Required
GEMINI_API_KEY=your_api_key_here

# Server (Optional)
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Storage (Optional)
CHROMA_PERSIST_DIR=./chroma_db
CORS_ORIGINS=*
```

## 💡 Usage Examples

### Example 1: Basic Legal Query

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What is IPC Section 302?","language":"English"}'
```

### Example 2: Section Expert Query

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain Section 498A IPC in detail","language":"English"}'
```

### Example 3: Legal Advice

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What should I do if arrested?","language":"English"}'
```

### Example 4: Hindi Query

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"धारा 420 क्या है?","language":"Hindi"}'
```

## 🎯 Agent Behavior

### Classifier Agent
- **Input**: Any legal query
- **Output**: Category (LAW_QUERY, SECTION_QUERY, LEGAL_ADVICE, etc.)
- **Confidence**: 0.0 - 1.0
- **Extracts**: Section numbers, law names, intent

### Section Expert
- **Input**: Query about specific section
- **Process**: Searches vector DB for context
- **Output**: Detailed explanation with:
  - Section text
  - Penalties
  - Examples
  - Related sections

### PDF Processor
- **Upload**: Chunks and embeds PDF
- **Query**: Semantic search + Gemini Q&A
- **Citations**: Page numbers and sources

### Router Agent
- **Decision**: Which agent to use
- **Fallback**: General assistant for non-legal queries

## 🔍 How It Works Internally

### 1. Query Processing Flow

```
User Query → Router → Agent Selection → Vector Search (if needed) 
→ Gemini Processing → Response Generation → User
```

### 2. Vector Storage

- **Embedding Model**: all-MiniLM-L6-v2 (384 dimensions)
- **Database**: ChromaDB (persistent local storage)
- **Similarity**: Cosine similarity
- **Retrieval**: Top-K most relevant chunks

### 3. Gemini Integration

- **Model**: gemini-1.5-flash
- **Features**: 
  - System instructions for role definition
  - Structured JSON output for classification
  - Long context window
  - Multilingual support

## 🎨 Customization

### Add New Agent

```python
# Create new agent in agents/my_agent.py
class MyAgent:
    def __init__(self):
        self.agent = GeminiChatAgent(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_name="gemini-1.5-flash",
            system_instruction="Your instructions here"
        )
    
    async def run(self, query, context=None):
        response = await self.agent.run(query)
        return {"result": response["text"]}
```

### Modify Routing Logic

Edit `agents/router.py`:

```python
# Add new route to system instruction
"MY_NEW_AGENT: For specific type of queries"

# Update route enum
"enum": ["...", "MY_NEW_AGENT"]
```

### Change Embedding Model

Edit `utils/vector_store.py`:

```python
self.embedding_model = SentenceTransformer('your-model-name')
```

## 📈 Performance

### Gemini Free Tier Limits

- **Rate Limit**: 15 requests per minute
- **Daily Limit**: 1,500 requests per day
- **Token Limit**: 32k input, 8k output

### ChromaDB Performance

- **Storage**: ~1MB per 1000 document chunks
- **Query Speed**: <100ms for most queries
- **Scalability**: Handles millions of vectors

### Local Embeddings

- **Speed**: ~50-100 docs/second
- **Model Size**: ~80MB (all-MiniLM-L6-v2)
- **Quality**: Good for most use cases

## ⚡ Optimization Tips

1. **Batch PDF Processing**: Process multiple PDFs together
2. **Cache Responses**: Cache common queries
3. **Increase Workers**: Use multiple uvicorn workers
4. **GPU Acceleration**: Use GPU for embeddings (optional)

## 🐛 Troubleshooting

### Issue: "GEMINI_API_KEY not found"
**Solution**: Check `.env` file exists and has valid key

### Issue: "Import errors"
**Solution**: Run `pip install -r requirements.txt`

### Issue: "ChromaDB errors"
**Solution**: Delete `chroma_db` folder and restart

### Issue: "Slow responses"
**Solution**: 
- Check internet connection (for Gemini)
- Reduce PDF chunk size
- Clear old documents

## 📚 Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Google Gemini 1.5 Flash | Text generation |
| Vector DB | ChromaDB | Document storage |
| Embeddings | Sentence Transformers | Local embeddings |
| Backend | FastAPI | REST API |
| PDF Processing | LangChain + PyPDF | PDF parsing |
| Environment | Python 3.9+ | Runtime |

## 🔒 Security Notes

- API key stored in `.env` (gitignored)
- Local vector storage (no external data sharing)
- No user data persisted beyond session
- CORS configurable

## 🚀 Deployment Options

### Option 1: Local Development
```cmd
python main.py
```

### Option 2: Production with Gunicorn
```cmd
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Option 3: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

## 📝 Next Steps

1. ✅ **Done**: Backend rebuilt with free services
2. 🎯 **TODO**: Connect React frontend
3. 🎯 **TODO**: Add voice features
4. 🎯 **TODO**: Deploy to cloud

## 🤝 Support

- Check logs for errors
- Verify `.env` configuration
- Test with `test_api.py`
- Check API docs at `/docs`

## 🎉 Summary

You now have a **fully functional agentic legal assistant** using:
- ✅ FREE Google Gemini
- ✅ FREE local vector storage
- ✅ FREE embeddings
- ✅ All features from original repo
- ✅ Improved architecture
- ✅ Better scalability

**Total Cost: $0.00/month** 🎊

---

**Happy Legal AI Building! 🚀**
