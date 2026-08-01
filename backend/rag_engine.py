import os
import re
import sys
from pathlib import Path
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding
from sentence_transformers import CrossEncoder
from groq import Groq

# Add backend directory to system path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import GROQ_API_KEY, QDRANT_PATH, QDRANT_COLLECTION, ROLE_COLLECTIONS
from backend.db_helper import execute_sql, get_schema_info

GROQ_MODEL = "llama-3.3-70b-versatile"

# Initialize singletons lazily
_qdrant_client = None
_dense_model = None
_sparse_model = None
_reranker = None
_groq_client = None

def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(path=str(QDRANT_PATH))
    return _qdrant_client

def get_dense_model():
    global _dense_model
    if _dense_model is None:
        _dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _dense_model

def get_sparse_model():
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = SparseTextEmbedding(model_name="prithvida/Splade_PP_en_v1")
    return _sparse_model

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("BAAI/bge-reranker-base")
    return _reranker

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Please add it to your backend/.env file.")
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def is_analytical_question(question: str) -> bool:
    """Classifies if a query is database-centric (SQL) or document-centric (Hybrid RAG)."""
    prompt = (
        "You are an assistant classifying queries for a hospital RAG system.\n"
        "We have two systems:\n"
        "1. DOCUMENT SEARCH: Standard procedures, drug lists, policies, and manual lookup.\n"
        "2. DATABASE QUERY (SQL): Analytical inquiries about stats, ticket counts, resolved/raised dates, billing amounts, or claims metrics.\n\n"
        "Return 'SQL' if the question requires counts, statistics, totals, or analytical aggregations of tickets or claims from a database.\n"
        "Otherwise, return 'DOCUMENT'. Respond with exactly one word: 'SQL' or 'DOCUMENT'.\n\n"
        f"Question: {question}"
    )
    try:
        groq_client = get_groq_client()
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.0
        )
        result = response.choices[0].message.content.strip().upper()
        return "SQL" in result
    except Exception as e:
        print(f"LLM Classification failed ({e}), using keyword fallback.")
        # Fallback keyword match
        keywords = ["how many", "count", "total", "average", "statistics", "amount", "tickets", "claims", "escalated", "resolved", "pending"]
        return any(k in question.lower() for k in keywords)


def clean_sql_query(raw_sql: str) -> str:
    """Extracts and cleans raw SQL queries from markdown or text formatting."""
    # Remove markdown code formatting blocks
    cleaned = re.sub(r"```(?:sql)?\s*(.*?)\s*```", r"\1", raw_sql, flags=re.DOTALL)
    cleaned = cleaned.strip()
    
    # Locate SQL commands
    match = re.search(r"\b(SELECT|WITH|UPDATE|DELETE|INSERT)\b.*", cleaned, re.IGNORECASE | re.DOTALL)
    if match:
        cleaned = match.group(0)
        
    return cleaned.strip()


def sql_rag_chain(question: str) -> dict:
    """SQL RAG implementation: translates natural language to SQL, executes it, and synthesizes answers."""
    schema_info = get_schema_info()
    prompt = (
        f"You are a SQL expert helper. Convert the user's question into a clean SQLite SQL query.\n"
        f"Do not write any explanation, introduction, or text. Only return the SQL query.\n"
        f"SQLite Database Schema:\n{schema_info}\n\n"
        f"Question: {question}"
    )
    
    try:
        groq_client = get_groq_client()
        # 1. Translate question to SQL
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.0
        )
        raw_sql = response.choices[0].message.content
        
        # 2. Clean SQL query
        sql_query = clean_sql_query(raw_sql)
        print(f"Generated SQL: {sql_query}")
        
        # 3. Execute SQL
        db_result = execute_sql(sql_query)
        
        if not db_result["success"]:
            error_msg = db_result.get("error", "Unknown database error")
            return {
                "answer": f"I was able to generate a SQL query but encountered an execution error: {error_msg}",
                "sources": [],
                "retrieval_type": "sql_rag",
                "sql_query": sql_query
            }
            
        # 4. Synthesize final answer using database output
        synthesis_context = f"SQL Query Run: {sql_query}\nColumns: {db_result['columns']}\nRows: {db_result['rows']}"
        synthesis_prompt = (
            f"You are MediBot, an operations assistant for MediAssist. Synthesize a natural language answer to the user's analytical question "
            f"using the SQLite database results below. Cite exact numbers and columns where appropriate.\n\n"
            f"Question: {question}\n\n"
            f"Database Context:\n{synthesis_context}"
        )
        
        synthesis_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": synthesis_prompt}],
            model=GROQ_MODEL,
            temperature=0.2
        )
        
        return {
            "answer": synthesis_response.choices[0].message.content,
            "sources": [],
            "retrieval_type": "sql_rag",
            "sql_query": sql_query
        }
        
    except Exception as e:
        return {
            "answer": f"Failed to execute SQL RAG process: {str(e)}",
            "sources": [],
            "retrieval_type": "sql_rag"
        }


def check_query_rbac_preflight(question: str, role: str) -> tuple[bool, str]:
    """Scans the query for keywords of restricted collections based on the user role.
    Returns (is_allowed, error_message).
    """
    question_lower = question.lower()
    
    # Define keywords representing each restricted category
    category_keywords = {
        "billing": ["billing", "claim", "insurer", "invoice", "payment", "cpt code"],
        "equipment": ["equipment", "ventilator", "dialysis", "maintenance manual", "calibration", "troubleshoot", "machinery"],
        "clinical": ["clinical", "treatment", "diagnosis", "drug formulary", "medical protocol", "sepsis", "dengue", "copd", "asthma", "diabetic"],
        "nursing": ["nursing", "icu procedure", "infection control", "catheter", "hygiene", "sanitiz", "five moments", "hand hygiene"]
    }
    
    allowed_categories = ROLE_COLLECTIONS.get(role, [])
    
    # Check if the user attempts to query a restricted category
    for category, keywords in category_keywords.items():
        if category not in allowed_categories:
            for kw in keywords:
                # Match word boundaries to prevent false positives
                if re.search(rf"\b{kw}s?\b", question_lower):
                    return False, f"Access Denied. You do not have permission to access the '{category}' documents or procedures."
                    
    return True, ""


def hybrid_rag_chain(question: str, role: str) -> dict:
    """Hybrid RAG implementation: retrieves filtered chunks from Qdrant, reranks, and answers."""
    # Enforce preflight RBAC scan
    is_allowed, error_msg = check_query_rbac_preflight(question, role)
    if not is_allowed:
        return {
            "answer": error_msg,
            "sources": [],
            "retrieval_type": "hybrid_rag"
        }
        
    try:
        client = get_qdrant_client()
        dense_model = get_dense_model()
        sparse_model = get_sparse_model()
        reranker = get_reranker()
        groq_client = get_groq_client()
        
        # Build RBAC metadata filter using roles
        rbac_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="access_roles",
                    match=models.MatchValue(value=role)
                )
            ]
        )
        
        # Generate embeddings for the query
        dense_query = list(dense_model.embed([question]))[0]
        sparse_query = list(sparse_model.embed([question]))[0]
        
        # Execute hybrid query with Reciprocal Rank Fusion (RRF)
        results = client.query_points(
            collection_name=QDRANT_COLLECTION,
            prefetch=[
                models.Prefetch(
                    query=dense_query.tolist(),
                    using="text-dense",
                    limit=15,
                    filter=rbac_filter
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_query.indices.tolist(),
                        values=sparse_query.values.tolist()
                    ),
                    using="text-sparse",
                    limit=15,
                    filter=rbac_filter
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=15
        )
        
        points = results.points
        
        if not points:
            # Check accessible collections to display helpful refuse message
            accessible_cols = ROLE_COLLECTIONS.get(role, [])
            cols_str = ", ".join(accessible_cols)
            return {
                "answer": f"I couldn't find any relevant documents in the collections you have access to. As a {role}, you can search the following collections: {cols_str}.",
                "sources": [],
                "retrieval_type": "hybrid_rag"
            }
            
        # Cross-Encoder Reranking
        pairs = [(question, p.payload["context_text"]) for p in points]
        scores = reranker.predict(pairs)
        
        # Rank by score
        scored_points = sorted(zip(points, scores), key=lambda x: x[1], reverse=True)
        
        # Display top 5 scores for development visibility
        print(f"Reranking scores for query '{question}':")
        for idx, (p, score) in enumerate(scored_points[:5]):
            print(f"  {idx+1}. Doc: {p.payload['source_document']} | Section: {p.payload['section_title']} | Rerank Score: {score:.4f}")
            
        # Select top 6 chunks for more comprehensive clinical/procedure coverage
        top_points = scored_points[:6]
        
        # Construct prompt context
        context_str = ""
        sources = []
        
        for p, score in top_points:
            payload = p.payload
            context_str += f"--- SOURCE: {payload['source_document']} | SECTION: {payload['section_title']} ---\n"
            context_str += f"{payload['context_text']}\n\n"
            
            # Record source citation (deduplicated)
            citation = {
                "source_document": payload["source_document"],
                "section_title": payload["section_title"],
                "collection": payload["collection"]
            }
            if citation not in sources:
                sources.append(citation)
            
        # System instructions
        system_instruction = (
            "You are MediBot, a helpful internal assistant for MediAssist Health Network.\n"
            "Answer the user's question exhaustively and comprehensively using only the provided context passages from our hospital policies, clinical guidelines, and manuals.\n"
            "CRITICAL: Critically evaluate the retrieved context passages. Only use chunks that are explicitly relevant to the disease or topic in the query. "
            "Do NOT apply guidelines from one disease or protocol (e.g., Sepsis broad-spectrum antimicrobial therapy, COPD exacerbation) to another disease (e.g., Dengue, pediatric fever) "
            "unless the text explicitly indicates they are related. If a retrieved passage is about a completely different disease, ignore it.\n"
            "Include step-by-step procedures, classification details, management workflows, and tables where available in the context.\n"
            "Cite the source documents and sections in your answer.\n\n"
            "CONTEXT GUARD: If the context passages do not contain the answer to the user's question (e.g., if the user asks about 'five moments of hand hygiene' but the provided context chunks are about 'leave policy' or 'billing codes'), you MUST respond with exactly: 'I cannot find the answer to this question in my available files.' Do NOT use your general pre-trained knowledge to answer under any circumstances if the topic is not covered in the context.\n\n"
            "FORMAT CONSTRAINT: At the end of your response, output a new line starting with 'Used Sections: ' followed by a comma-separated list of the exact section titles of the context passages you actually used to formulate the answer. Do NOT list sections that you ignored or declared irrelevant.\n"
            "Example format:\n"
            "Used Sections: Temperature-based approach, Classification"
        )
        
        user_prompt = f"Context passages:\n{context_str}\n\nQuestion: {question}"
        
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            model=GROQ_MODEL,
            temperature=0.3
        )
        
        raw_answer = response.choices[0].message.content
        used_sections = []
        
        # Parse Used Sections
        used_match = re.search(r"Used Sections:\s*(.*)", raw_answer, re.IGNORECASE)
        if used_match:
            sections_raw = used_match.group(1).split(",")
            used_sections = [s.strip().lower() for s in sections_raw if s.strip()]
            # Remove the "Used Sections:" line from the final user-facing answer text
            clean_answer = re.sub(r"\n*Used Sections:\s*.*", "", raw_answer, flags=re.IGNORECASE).strip()
        else:
            clean_answer = raw_answer.strip()
            
        # Filter citations to only include chunks marked as used by the LLM
        final_sources = []
        for src in sources:
            src_title_lower = src["section_title"].lower()
            # Check if this section was explicitly listed, or is a subsegment
            if not used_sections or src_title_lower in used_sections or any(u in src_title_lower for u in used_sections):
                final_sources.append(src)
                
        return {
            "answer": clean_answer,
            "sources": final_sources,
            "retrieval_type": "hybrid_rag"
        }
        
    except Exception as e:
        return {
            "answer": f"Error running hybrid RAG search: {str(e)}",
            "sources": [],
            "retrieval_type": "hybrid_rag"
        }
