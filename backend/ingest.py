import os
import sys
from pathlib import Path
import uuid
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

# Add backend to path if needed
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import DATA_DIR, QDRANT_PATH, QDRANT_COLLECTION

# Inverted Role mapping from instruction matrix
COLLECTION_ROLES = {
    "general": ["doctor", "nurse", "billing_executive", "technician", "admin"],
    "clinical": ["doctor", "admin"],
    "nursing": ["nurse", "doctor", "admin"],
    "billing": ["billing_executive", "admin"],
    "equipment": ["technician", "admin"]
}

def get_chunk_type(chunk) -> str:
    """Detects the chunk type based on doc_items labels."""
    labels_str = []
    for item in getattr(chunk.meta, "doc_items", []):
        label_val = getattr(item, "label", "")
        if hasattr(label_val, "value"):
            labels_str.append(str(label_val.value).lower())
        else:
            labels_str.append(str(label_val).lower())
            
    if "table" in labels_str:
        return "table"
    elif "code" in labels_str:
        return "code"
    elif any(lbl in labels_str for lbl in ["title", "section_header", "heading"]):
        return "heading"
    return "text"

def main():
    print("Initializing Qdrant Client...")
    # Initialize Qdrant Client in local file-storage mode
    client = QdrantClient(path=str(QDRANT_PATH))
    
    # Initialize FastEmbed dense and sparse models
    print("Loading embedding models (FastEmbed BGE-small & Splade)...")
    dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    sparse_model = SparseTextEmbedding(model_name="prithvida/Splade_PP_en_v1")
    
    # Recreate Qdrant Collection
    print(f"Creating/Recreating collection '{QDRANT_COLLECTION}'...")
    try:
        client.get_collection(QDRANT_COLLECTION)
        client.delete_collection(QDRANT_COLLECTION)
        print("Existing collection deleted.")
    except Exception:
        pass
        
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config={
            "text-dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
        },
        sparse_vectors_config={
            "text-sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False)
            )
        }
    )
    print("Collection created successfully.")
    
    # Document converter
    print("Initializing Docling Document Converter...")
    converter = DocumentConverter()
    chunker = HybridChunker(max_tokens=512, merge_peers=True)
    
    # Walk through folders
    print("Scanning directories for documents...")
    all_points = []
    
    # Supported categories
    categories = ["general", "clinical", "nursing", "billing", "equipment"]
    
    for category in categories:
        cat_dir = DATA_DIR / category
        if not cat_dir.exists():
            print(f"Warning: Directory {cat_dir} does not exist.")
            continue
            
        print(f"\nProcessing category: {category}")
        allowed_roles = COLLECTION_ROLES[category]
        
        # List all files (PDF and MD)
        files = list(cat_dir.glob("*.pdf")) + list(cat_dir.glob("*.md"))
        for file_path in files:
            print(f" - Parsing {file_path.name}...")
            try:
                # Convert PDF/MD using Docling
                result = converter.convert(str(file_path))
                doc = result.document
                
                # Chunk document
                chunks = list(chunker.chunk(doc))
                print(f"   Extracted {len(chunks)} chunks.")
                
                texts_to_embed = []
                payloads = []
                
                for idx, chunk in enumerate(chunks):
                    # Resolve headings path
                    headings = getattr(chunk.meta, "headings", [])
                    section_title = " / ".join(headings) if headings else "General"
                    
                    # Prepend context to the text
                    parent_context = f"Document: {file_path.name}\nSection: {section_title}\n"
                    context_chunk_text = parent_context + chunk.text
                    
                    chunk_type = get_chunk_type(chunk)
                    
                    texts_to_embed.append(context_chunk_text)
                    payloads.append({
                        "source_document": file_path.name,
                        "collection": category,
                        "access_roles": allowed_roles,
                        "section_title": section_title,
                        "chunk_type": chunk_type,
                        "text": chunk.text,  # store the raw text without prepended headers for displaying
                        "context_text": context_chunk_text  # store context-prefixed text
                    })
                
                if not texts_to_embed:
                    continue
                    
                # Generate embeddings
                print("   Generating dense and sparse embeddings...")
                dense_embeddings = list(dense_model.embed(texts_to_embed))
                sparse_embeddings = list(sparse_model.embed(texts_to_embed))
                
                # Create points for Qdrant
                for i in range(len(texts_to_embed)):
                    point_id = str(uuid.uuid4())
                    
                    # Prepare sparse vector details
                    indices = sparse_embeddings[i].indices.tolist()
                    values = sparse_embeddings[i].values.tolist()
                    
                    point = models.PointStruct(
                        id=point_id,
                        vector={
                            "text-dense": dense_embeddings[i].tolist(),
                            "text-sparse": models.SparseVector(
                                indices=indices,
                                values=values
                            )
                        },
                        payload=payloads[i]
                    )
                    all_points.append(point)
                    
            except Exception as e:
                print(f"Error parsing file {file_path.name}: {e}")
                
    # Upload points to Qdrant
    if all_points:
        print(f"\nUploading {len(all_points)} points to Qdrant...")
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=all_points
        )
        print("Ingestion completed successfully!")
    else:
        print("No documents ingested.")

if __name__ == "__main__":
    main()
