"""
Enhanced Seed Database Script

Populates the vector database with 500+ legal documents from 15 Indian acts.
Features:
- Parallel processing with 4 workers
- File validation and error handling
- Automatic backup before seeding
- Progress bars with tqdm
- Enhanced metadata extraction
- Support for 13+ seed files
"""

import asyncio
import sys
import os
import shutil
import argparse
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.vector_store import get_vector_store
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SeedFileValidator:
    """Validates seed data files before processing."""

    def __init__(self):
        self.min_file_size = 100  # bytes
        self.max_file_size = 50 * 1024 * 1024  # 50 MB
        self.required_encoding = 'utf-8'

    def validate_file(self, filepath: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a seed file.

        Args:
            filepath: Path to seed file

        Returns:
            (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not filepath.exists():
                return False, f"File not found: {filepath}"

            # Check file size
            file_size = filepath.stat().st_size
            if file_size < self.min_file_size:
                return False, f"File too small ({file_size} bytes)"

            if file_size > self.max_file_size:
                return False, f"File too large ({file_size} bytes)"

            # Check encoding
            try:
                with open(filepath, 'r', encoding=self.required_encoding) as f:
                    content = f.read()
            except UnicodeDecodeError:
                return False, f"File encoding is not {self.required_encoding}"

            # Check content is not empty
            if not content.strip():
                return False, "File content is empty"

            # Basic content validation
            if len(content.split()) < 50:
                return False, "File content too short (less than 50 words)"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"


class MetadataExtractor:
    """Extracts enhanced metadata from legal documents."""

    def __init__(self):
        # Patterns for extracting section numbers
        self.section_patterns = [
            r'Section\s+(\d+[A-Z]?)',
            r'Article\s+(\d+[A-Z]?)',
            r'BNS\s+(\d+)',
            r'BNSS\s+(\d+)',
            r'BSA\s+(\d+)',
            r'IPC\s+(\d+)',
        ]

    def extract_metadata(
        self,
        chunk: str,
        filename: str,
        title: str,
        chunk_id: int,
        total_chunks: int
    ) -> Dict:
        """
        Extract metadata from document chunk.

        Args:
            chunk: Text chunk
            filename: Source filename
            title: Document title
            chunk_id: Chunk index
            total_chunks: Total number of chunks

        Returns:
            Metadata dictionary
        """
        metadata = {
            "source": filename,
            "title": title,
            "chunk_id": chunk_id,
            "total_chunks": total_chunks,
            "law_type": self._get_law_type(filename),
            "act_name": self._get_act_name(filename),
            "section_number": self._extract_section_number(chunk) or "",
            "keywords": ", ".join(self._extract_keywords(chunk)),
            "chunk_length": len(chunk)
        }

        return metadata

    def _get_law_type(self, filename: str) -> str:
        """Determine law type from filename."""
        filename_lower = filename.lower()

        if 'criminal' in filename_lower or 'bns' in filename_lower or 'ipc' in filename_lower:
            return "criminal"
        elif 'civil' in filename_lower or 'contract' in filename_lower or 'property' in filename_lower:
            return "civil"
        elif 'constitution' in filename_lower:
            return "constitutional"
        elif 'procedural' in filename_lower or 'bnss' in filename_lower or 'crpc' in filename_lower:
            return "procedural"
        elif 'evidence' in filename_lower or 'bsa' in filename_lower:
            return "evidence"
        elif 'traffic' in filename_lower or 'motor' in filename_lower:
            return "traffic"
        elif 'consumer' in filename_lower:
            return "consumer"
        elif 'commercial' in filename_lower or 'companies' in filename_lower or 'arbitration' in filename_lower:
            return "commercial"
        else:
            return "general"

    def _get_act_name(self, filename: str) -> str:
        """Extract act name from filename."""
        # Remove extension and replace underscores
        name = filename.replace('.txt', '').replace('_', ' ').title()
        return name

    def _extract_section_number(self, text: str) -> Optional[str]:
        """Extract section/article number from text."""
        for pattern in self.section_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Common legal keywords
        legal_keywords = [
            'punishment', 'imprisonment', 'fine', 'bail', 'cognizable', 'non-cognizable',
            'bailable', 'non-bailable', 'offense', 'crime', 'rights', 'fundamental',
            'procedure', 'evidence', 'witness', 'investigation', 'arrest', 'charge',
            'trial', 'appeal', 'acquittal', 'conviction', 'sentence', 'compensation'
        ]

        found_keywords = []
        text_lower = text.lower()

        for keyword in legal_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords[:5]  # Return top 5 keywords


class DatabaseSeeder:
    """Main database seeding class with parallel processing."""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        num_workers: int = 4,
        backup_enabled: bool = True
    ):
        """
        Initialize database seeder.

        Args:
            chunk_size: Size of text chunks (default: 800)
            chunk_overlap: Overlap between chunks (default: 150)
            num_workers: Number of parallel workers (default: 4)
            backup_enabled: Enable automatic backup (default: True)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.num_workers = num_workers
        self.backup_enabled = backup_enabled

        self.validator = SeedFileValidator()
        self.metadata_extractor = MetadataExtractor()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        logger.info(f"DatabaseSeeder initialized (chunk_size={chunk_size}, workers={num_workers})")

    def backup_database(self, persist_dir: str) -> Optional[str]:
        """
        Backup existing ChromaDB database.

        Args:
            persist_dir: ChromaDB persistence directory

        Returns:
            Backup directory path or None if failed
        """
        if not self.backup_enabled:
            logger.info("Backup disabled, skipping...")
            return None

        persist_path = Path(persist_dir)

        if not persist_path.exists():
            logger.info("No existing database to backup")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = persist_path.parent / f"chroma_db_backup_{timestamp}"

            logger.info(f"📦 Creating backup: {backup_dir}")
            shutil.copytree(persist_path, backup_dir)

            logger.info(f"✅ Backup created successfully")
            return str(backup_dir)

        except Exception as e:
            logger.error(f"❌ Backup failed: {str(e)}")
            return None

    def validate_all_files(self, files: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Validate all seed files before processing.

        Args:
            files: List of (filename, title) tuples

        Returns:
            List of valid files
        """
        logger.info("🔍 Validating seed files...")

        seed_dir = Path(__file__).parent / "seed_data"
        valid_files = []

        for filename, title in files:
            filepath = seed_dir / filename
            is_valid, error_msg = self.validator.validate_file(filepath)

            if is_valid:
                logger.info(f"✅ {filename} - Valid")
                valid_files.append((filename, title))
            else:
                logger.warning(f"⚠️ {filename} - Invalid: {error_msg}")

        logger.info(f"Validation complete: {len(valid_files)}/{len(files)} files valid\n")
        return valid_files

    def process_file(self, filename: str, title: str) -> Dict:
        """
        Process a single seed file.

        Args:
            filename: Seed filename
            title: Document title

        Returns:
            Processing result dictionary
        """
        seed_dir = Path(__file__).parent / "seed_data"
        filepath = seed_dir / filename

        result = {
            "filename": filename,
            "success": False,
            "chunks_added": 0,
            "error": None
        }

        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split into chunks
            chunks = self.text_splitter.split_text(content)

            # Prepare documents with enhanced metadata
            texts = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                texts.append(chunk)

                metadata = self.metadata_extractor.extract_metadata(
                    chunk=chunk,
                    filename=filename,
                    title=title,
                    chunk_id=i,
                    total_chunks=len(chunks)
                )
                metadatas.append(metadata)

            result["chunks_added"] = len(chunks)
            result["texts"] = texts
            result["metadatas"] = metadatas
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Error processing {filename}: {str(e)}")

        return result

    async def seed_database(self, files: List[Tuple[str, str]], validate: bool = True):
        """
        Seed database with multiple files using parallel processing.

        Args:
            files: List of (filename, title) tuples
            validate: Enable file validation (default: True)
        """
        logger.info("🌱 Starting enhanced database seeding...")
        logger.info(f"📊 Configuration: chunk_size={self.chunk_size}, overlap={self.chunk_overlap}, workers={self.num_workers}\n")

        # Validate files
        if validate:
            files = self.validate_all_files(files)

        if not files:
            logger.error("❌ No valid files to process")
            return

        # Backup database
        vector_store = get_vector_store()
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.backup_database(persist_dir)

        # Process files in parallel
        logger.info(f"⚙️ Processing {len(files)} files with {self.num_workers} workers...\n")

        all_results = []

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.process_file, filename, title): (filename, title)
                for filename, title in files
            }

            # Track progress
            with tqdm(total=len(files), desc="Processing files", unit="file") as pbar:
                for future in as_completed(future_to_file):
                    result = future.result()
                    all_results.append(result)
                    pbar.update(1)

                    if result["success"]:
                        pbar.set_postfix({"last": result["filename"], "chunks": result["chunks_added"]})

        # Add all documents to vector store
        logger.info("\n📝 Adding documents to vector store...")

        total_chunks = 0
        successful_files = 0
        failed_files = 0

        for result in tqdm(all_results, desc="Adding to vector store", unit="file"):
            if not result["success"]:
                failed_files += 1
                continue

            try:
                # Generate unique IDs
                import uuid
                num_chunks = len(result["texts"])
                ids = [f"{result['filename']}_{uuid.uuid4().hex[:8]}" for _ in range(num_chunks)]

                # Add to vector store
                vector_store.add_documents(
                    documents=result["texts"],
                    metadatas=result["metadatas"],
                    ids=ids
                )

                total_chunks += result["chunks_added"]
                successful_files += 1

            except Exception as e:
                logger.error(f"❌ Error adding {result['filename']} to vector store: {str(e)}")
                failed_files += 1

        # Get final stats
        stats = vector_store.get_stats()

        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 Database seeding complete!")
        logger.info(f"{'='*80}")
        logger.info(f"📊 Files processed: {successful_files} successful, {failed_files} failed")
        logger.info(f"📊 Total chunks added: {total_chunks}")
        logger.info(f"📊 Total documents in database: {stats['total_documents']}")
        logger.info(f"📊 Collections: {len(stats.get('collections', []))}")
        logger.info(f"{'='*80}\n")


# Define all seed files (13 files covering 15+ acts)
SEED_FILES = [
    # Criminal Law (BNS replaces IPC 1860)
    ("bns_sections.txt", "Bharatiya Nyaya Sanhita 2023 - Criminal Law"),

    # Procedural Law (BNSS replaces CrPC 1973)
    ("bnss_sections.txt", "Bharatiya Nagarik Suraksha Sanhita 2023 - Criminal Procedure"),

    # Evidence Law (BSA replaces Evidence Act 1872)
    ("bsa_sections.txt", "Bharatiya Sakshya Adhiniyam 2023 - Evidence Law"),

    # Constitution
    ("constitution_rights.txt", "Constitution of India - Fundamental Rights"),
    ("constitution_dpsp.txt", "Constitution of India - Directive Principles"),

    # Civil Laws
    ("contract_act.txt", "Indian Contract Act 1872"),
    ("transfer_of_property.txt", "Transfer of Property Act 1882"),
    ("partnership_act.txt", "Indian Partnership Act 1932"),

    # Consumer & Social Protection
    ("consumer_protection.txt", "Consumer Protection Act 2019"),
    ("pocso_act.txt", "POCSO Act 2012 - Child Protection"),
    ("domestic_violence.txt", "Protection of Women from Domestic Violence Act 2005"),
    ("sc_st_act.txt", "SC/ST Prevention of Atrocities Act 1989"),

    # Administrative & Commercial
    ("rti_act.txt", "Right to Information Act 2005"),
    ("arbitration_act.txt", "Arbitration and Conciliation Act 1996"),
    ("companies_act.txt", "Companies Act 2013"),

    # Legacy files (for backward compatibility)
    ("traffic_laws.txt", "Indian Traffic Laws - Motor Vehicles Act 1988"),
    ("common_ipc_sections.txt", "Common IPC Sections - Indian Penal Code (Legacy)")
]


async def main():
    """Main entry point with CLI arguments."""
    parser = argparse.ArgumentParser(description="Seed legal database with enhanced features")

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Only validate files without seeding'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Disable automatic backup'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=800,
        help='Chunk size for text splitting (default: 800)'
    )

    args = parser.parse_args()

    # Initialize seeder
    seeder = DatabaseSeeder(
        chunk_size=args.chunk_size,
        chunk_overlap=150,
        num_workers=args.workers,
        backup_enabled=not args.no_backup
    )

    # Validate only mode
    if args.validate:
        logger.info("Running in validation-only mode\n")
        valid_files = seeder.validate_all_files(SEED_FILES)
        logger.info(f"\n✅ Validation complete: {len(valid_files)}/{len(SEED_FILES)} files valid")
        return

    # Full seeding
    await seeder.seed_database(SEED_FILES)


if __name__ == "__main__":
    asyncio.run(main())
