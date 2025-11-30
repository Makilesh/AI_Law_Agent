"""
Seed the vector database with basic legal information.
Run this once to populate the database with common legal knowledge.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.vector_store import get_vector_store
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_database():
    """Seed the database with basic legal information."""
    logger.info("🌱 Starting database seeding...")
    
    # Initialize vector store
    vector_store = get_vector_store()
    
    # Text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    # Load seed data files
    seed_dir = Path(__file__).parent / "seed_data"
    
    files = [
        ("traffic_laws.txt", "Indian Traffic Laws - Motor Vehicles Act 1988"),
        ("common_ipc_sections.txt", "Common IPC Sections - Indian Penal Code")
    ]
    
    total_chunks = 0
    
    for filename, title in files:
        filepath = seed_dir / filename
        
        if not filepath.exists():
            logger.warning(f"⚠️ File not found: {filepath}")
            continue
        
        logger.info(f"📄 Processing {filename}...")
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into chunks
        chunks = text_splitter.split_text(content)
        
        # Prepare documents for vector store
        texts = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "source": filename,
                "title": title,
                "chunk_id": i,
                "total_chunks": len(chunks)
            })
        
        # Add to vector store
        try:
            # Generate unique IDs
            import uuid
            ids = [f"{filename}_{uuid.uuid4().hex[:8]}" for _ in range(len(chunks))]
            
            vector_store.add_documents(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ Added {len(chunks)} chunks from {filename}")
            total_chunks += len(chunks)
        except Exception as e:
            logger.error(f"❌ Error adding {filename}: {e}")
    
    # Get final stats
    stats = vector_store.get_stats()
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 Database seeding complete!")
    logger.info(f"📊 Total chunks added: {total_chunks}")
    logger.info(f"📊 Total documents in database: {stats['total_documents']}")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(seed_database())
