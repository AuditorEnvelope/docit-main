"""
Indexer Service - Vector DB Integration for RAG
Generates embeddings and stores in Milvus for semantic search
"""

import os
import json
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncpg
from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema, DataType,
    utility
)

# Try multiple embedding providers
try:
    import openai
    HAS_OPENAI = True
except:
    HAS_OPENAI = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except:
    HAS_GEMINI = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_LOCAL = True
except:
    HAS_LOCAL = False

@dataclass
class EmbeddingEntry:
    """Entry in vector database"""
    id: str
    embedding: List[float]
    content: str
    type: str  # doc_node|code_snippet|diff|overlay
    repo_id: str
    commit_sha: str
    node_id: str
    metadata: Dict

class IndexerService:
    """
    Indexer Service - Manages vector embeddings for semantic search
    
    Features:
    - Generate embeddings using OpenAI
    - Store in Milvus vector DB
    - Semantic search with provenance
    - Batch indexing
    """
    
    def __init__(self, milvus_host: str = "localhost", milvus_port: str = "19530"):
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = "doc_embeddings"
        self.collection = None
        
        # Try to initialize embedding provider (priority order)
        self.embedding_provider = None
        
        # 1. Try OpenAI
        if HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.embedding_provider = "openai"
            print("✅ Using OpenAI for embeddings")
        
        # 2. Try Gemini
        elif HAS_GEMINI and os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.embedding_provider = "gemini"
            print("✅ Using Gemini for embeddings")
        
        # 3. Use local model (FREE!)
        elif HAS_LOCAL:
            self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_provider = "local"
            print("✅ Using FREE local embeddings (no API key needed!)")
        
        else:
            raise ValueError("No embedding provider available! Install: pip install sentence-transformers")
    
    def connect(self):
        """Connect to Milvus"""
        print(f"🔌 Connecting to Milvus at {self.milvus_host}:{self.milvus_port}")
        connections.connect(
            alias="default",
            host=self.milvus_host,
            port=self.milvus_port
        )
        
        # Create collection if doesn't exist
        if not utility.has_collection(self.collection_name):
            self.create_collection()
        
        self.collection = Collection(self.collection_name)
        self.collection.load()
        print(f"✅ Connected to collection: {self.collection_name}")
    
    def create_collection(self):
        """Create Milvus collection with schema"""
        print(f"📦 Creating collection: {self.collection_name}")
        
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=200, is_primary=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="repo_id", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="commit_sha", dtype=DataType.VARCHAR, max_length=40),
            FieldSchema(name="node_id", dtype=DataType.VARCHAR, max_length=200),
        ]
        
        schema = CollectionSchema(fields, description="Documentation embeddings")
        collection = Collection(self.collection_name, schema)
        
        # Create index for vector field
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index("embedding", index_params)
        print(f"✅ Collection created with index")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using available provider
        
        Priority: OpenAI > Gemini > Local (FREE)
        """
        try:
            if self.embedding_provider == "openai":
                # OpenAI embeddings
                response = await openai.Embedding.acreate(
                    model="text-embedding-3-small",
                    input=text
                )
                return response['data'][0]['embedding']
            
            elif self.embedding_provider == "gemini":
                # Gemini embeddings (FREE with API key!)
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text
                )
                return result['embedding']
            
            elif self.embedding_provider == "local":
                # Local embeddings (100% FREE, no API key!)
                return self.local_model.encode(text).tolist()
            
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise
    
    async def index_node(self, node: Dict) -> str:
        """
        Index a documentation node
        
        Args:
            node: Doc node dictionary with id, content, metadata
        
        Returns: Vector ID
        """
        # Prepare content for embedding
        content_parts = [
            node.get('title', ''),
            node.get('content', {}).get('description', ''),
            node.get('content', {}).get('signature', '')
        ]
        content_text = '\n'.join([p for p in content_parts if p])
        
        # Generate embedding
        embedding = await self.generate_embedding(content_text)
        
        # Prepare entry
        entry = EmbeddingEntry(
            id=node['id'],
            embedding=embedding,
            content=content_text[:10000],  # Truncate if too long
            type='doc_node',
            repo_id=node.get('metadata', {}).get('repo_id', ''),
            commit_sha=node.get('commit_sha', ''),
            node_id=node['id'],
            metadata=node.get('metadata', {})
        )
        
        # Insert to Milvus
        self.collection.insert([
            [entry.id],
            [entry.embedding],
            [entry.content],
            [entry.type],
            [entry.repo_id],
            [entry.commit_sha],
            [entry.node_id]
        ])
        
        return entry.id
    
    async def index_batch(self, nodes: List[Dict]) -> List[str]:
        """
        Index multiple nodes in batch
        
        More efficient than indexing one by one
        """
        print(f"📝 Indexing batch of {len(nodes)} nodes...")
        
        ids = []
        embeddings = []
        contents = []
        types = []
        repo_ids = []
        commit_shas = []
        node_ids = []
        
        for node in nodes:
            # Prepare content
            content_parts = [
                node.get('title', ''),
                node.get('content', {}).get('description', ''),
                node.get('content', {}).get('signature', '')
            ]
            content_text = '\n'.join([p for p in content_parts if p])
            
            # Generate embedding
            embedding = await self.generate_embedding(content_text)
            
            # Append to lists
            ids.append(node['id'])
            embeddings.append(embedding)
            contents.append(content_text[:10000])
            types.append('doc_node')
            repo_ids.append(node.get('metadata', {}).get('repo_id', ''))
            commit_shas.append(node.get('commit_sha', ''))
            node_ids.append(node['id'])
        
        # Batch insert
        self.collection.insert([
            ids, embeddings, contents, types, repo_ids, commit_shas, node_ids
        ])
        
        print(f"✅ Indexed {len(nodes)} nodes")
        return ids
    
    async def search(
        self, 
        query: str, 
        top_k: int = 5,
        repo_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Semantic search for relevant documentation
        
        Args:
            query: Search query
            top_k: Number of results
            repo_id: Filter by repository (optional)
        
        Returns: List of results with content and provenance
        """
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        
        # Search parameters
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        
        # Filter expression
        expr = None
        if repo_id:
            expr = f'repo_id == "{repo_id}"'
        
        # Search
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content", "type", "repo_id", "commit_sha", "node_id"]
        )
        
        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "id": hit.id,
                "score": float(hit.distance),
                "content": hit.entity.get("content"),
                "type": hit.entity.get("type"),
                "provenance": {
                    "repo_id": hit.entity.get("repo_id"),
                    "commit_sha": hit.entity.get("commit_sha"),
                    "node_id": hit.entity.get("node_id")
                }
            })
        
        return formatted_results
    
    async def delete_node(self, node_id: str):
        """Delete node from index"""
        self.collection.delete(f'id == "{node_id}"')
    
    async def delete_repo(self, repo_id: str):
        """Delete all nodes for a repository"""
        self.collection.delete(f'repo_id == "{repo_id}"')
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return {
            "total_entities": self.collection.num_entities,
            "collection_name": self.collection_name
        }


# CLI for testing
if __name__ == "__main__":
    import sys
    
    async def main():
        indexer = IndexerService()
        indexer.connect()
        
        if len(sys.argv) > 1 and sys.argv[1] == "search":
            # Search mode
            query = " ".join(sys.argv[2:])
            print(f"\n🔍 Searching for: {query}")
            results = await indexer.search(query, top_k=3)
            
            print(f"\n📊 Found {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. Score: {result['score']:.4f}")
                print(f"   Content: {result['content'][:200]}...")
                print(f"   Provenance: {result['provenance']}")
                print()
        else:
            # Stats mode
            stats = indexer.get_stats()
            print(f"\n📊 Collection Stats:")
            print(f"   Total entities: {stats['total_entities']}")
            print(f"   Collection: {stats['collection_name']}")
    
    asyncio.run(main())

"""
Indexer Service - Vector DB Integration for RAG
Generates embeddings and stores in Milvus for semantic search
"""

import os
import json
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncpg
from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema, DataType,
    utility
)

# Try multiple embedding providers
try:
    import openai
    HAS_OPENAI = True
except:
    HAS_OPENAI = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except:
    HAS_GEMINI = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_LOCAL = True
except:
    HAS_LOCAL = False

@dataclass
class EmbeddingEntry:
    """Entry in vector database"""
    id: str
    embedding: List[float]
    content: str
    type: str  # doc_node|code_snippet|diff|overlay
    repo_id: str
    commit_sha: str
    node_id: str
    metadata: Dict

class IndexerService:
    """
    Indexer Service - Manages vector embeddings for semantic search
    
    Features:
    - Generate embeddings using OpenAI
    - Store in Milvus vector DB
    - Semantic search with provenance
    - Batch indexing
    """
    
    def __init__(self, milvus_host: str = "localhost", milvus_port: str = "19530"):
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = "doc_embeddings"
        self.collection = None
        
        # Try to initialize embedding provider (priority order)
        self.embedding_provider = None
        
        # 1. Try OpenAI
        if HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.embedding_provider = "openai"
            print("✅ Using OpenAI for embeddings")
        
        # 2. Try Gemini
        elif HAS_GEMINI and os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.embedding_provider = "gemini"
            print("✅ Using Gemini for embeddings")
        
        # 3. Use local model (FREE!)
        elif HAS_LOCAL:
            self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_provider = "local"
            print("✅ Using FREE local embeddings (no API key needed!)")
        
        else:
            raise ValueError("No embedding provider available! Install: pip install sentence-transformers")
    
    def connect(self):
        """Connect to Milvus"""
        print(f"🔌 Connecting to Milvus at {self.milvus_host}:{self.milvus_port}")
        connections.connect(
            alias="default",
            host=self.milvus_host,
            port=self.milvus_port
        )
        
        # Create collection if doesn't exist
        if not utility.has_collection(self.collection_name):
            self.create_collection()
        
        self.collection = Collection(self.collection_name)
        self.collection.load()
        print(f"✅ Connected to collection: {self.collection_name}")
    
    def create_collection(self):
        """Create Milvus collection with schema"""
        print(f"📦 Creating collection: {self.collection_name}")
        
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=200, is_primary=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="repo_id", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="commit_sha", dtype=DataType.VARCHAR, max_length=40),
            FieldSchema(name="node_id", dtype=DataType.VARCHAR, max_length=200),
        ]
        
        schema = CollectionSchema(fields, description="Documentation embeddings")
        collection = Collection(self.collection_name, schema)
        
        # Create index for vector field
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index("embedding", index_params)
        print(f"✅ Collection created with index")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using available provider
        
        Priority: OpenAI > Gemini > Local (FREE)
        """
        try:
            if self.embedding_provider == "openai":
                # OpenAI embeddings
                response = await openai.Embedding.acreate(
                    model="text-embedding-3-small",
                    input=text
                )
                return response['data'][0]['embedding']
            
            elif self.embedding_provider == "gemini":
                # Gemini embeddings (FREE with API key!)
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text
                )
                return result['embedding']
            
            elif self.embedding_provider == "local":
                # Local embeddings (100% FREE, no API key!)
                return self.local_model.encode(text).tolist()
            
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise
    
    async def index_node(self, node: Dict) -> str:
        """
        Index a documentation node
        
        Args:
            node: Doc node dictionary with id, content, metadata
        
        Returns: Vector ID
        """
        # Prepare content for embedding
        content_parts = [
            node.get('title', ''),
            node.get('content', {}).get('description', ''),
            node.get('content', {}).get('signature', '')
        ]
        content_text = '\n'.join([p for p in content_parts if p])
        
        # Generate embedding
        embedding = await self.generate_embedding(content_text)
        
        # Prepare entry
        entry = EmbeddingEntry(
            id=node['id'],
            embedding=embedding,
            content=content_text[:10000],  # Truncate if too long
            type='doc_node',
            repo_id=node.get('metadata', {}).get('repo_id', ''),
            commit_sha=node.get('commit_sha', ''),
            node_id=node['id'],
            metadata=node.get('metadata', {})
        )
        
        # Insert to Milvus
        self.collection.insert([
            [entry.id],
            [entry.embedding],
            [entry.content],
            [entry.type],
            [entry.repo_id],
            [entry.commit_sha],
            [entry.node_id]
        ])
        
        return entry.id
    
    async def index_batch(self, nodes: List[Dict]) -> List[str]:
        """
        Index multiple nodes in batch
        
        More efficient than indexing one by one
        """
        print(f"📝 Indexing batch of {len(nodes)} nodes...")
        
        ids = []
        embeddings = []
        contents = []
        types = []
        repo_ids = []
        commit_shas = []
        node_ids = []
        
        for node in nodes:
            # Prepare content
            content_parts = [
                node.get('title', ''),
                node.get('content', {}).get('description', ''),
                node.get('content', {}).get('signature', '')
            ]
            content_text = '\n'.join([p for p in content_parts if p])
            
            # Generate embedding
            embedding = await self.generate_embedding(content_text)
            
            # Append to lists
            ids.append(node['id'])
            embeddings.append(embedding)
            contents.append(content_text[:10000])
            types.append('doc_node')
            repo_ids.append(node.get('metadata', {}).get('repo_id', ''))
            commit_shas.append(node.get('commit_sha', ''))
            node_ids.append(node['id'])
        
        # Batch insert
        self.collection.insert([
            ids, embeddings, contents, types, repo_ids, commit_shas, node_ids
        ])
        
        print(f"✅ Indexed {len(nodes)} nodes")
        return ids
    
    async def search(
        self, 
        query: str, 
        top_k: int = 5,
        repo_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Semantic search for relevant documentation
        
        Args:
            query: Search query
            top_k: Number of results
            repo_id: Filter by repository (optional)
        
        Returns: List of results with content and provenance
        """
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        
        # Search parameters
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        
        # Filter expression
        expr = None
        if repo_id:
            expr = f'repo_id == "{repo_id}"'
        
        # Search
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content", "type", "repo_id", "commit_sha", "node_id"]
        )
        
        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "id": hit.id,
                "score": float(hit.distance),
                "content": hit.entity.get("content"),
                "type": hit.entity.get("type"),
                "provenance": {
                    "repo_id": hit.entity.get("repo_id"),
                    "commit_sha": hit.entity.get("commit_sha"),
                    "node_id": hit.entity.get("node_id")
                }
            })
        
        return formatted_results
    
    async def delete_node(self, node_id: str):
        """Delete node from index"""
        self.collection.delete(f'id == "{node_id}"')
    
    async def delete_repo(self, repo_id: str):
        """Delete all nodes for a repository"""
        self.collection.delete(f'repo_id == "{repo_id}"')
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return {
            "total_entities": self.collection.num_entities,
            "collection_name": self.collection_name
        }


# CLI for testing
if __name__ == "__main__":
    import sys
    
    async def main():
        indexer = IndexerService()
        indexer.connect()
        
        if len(sys.argv) > 1 and sys.argv[1] == "search":
            # Search mode
            query = " ".join(sys.argv[2:])
            print(f"\n🔍 Searching for: {query}")
            results = await indexer.search(query, top_k=3)
            
            print(f"\n📊 Found {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. Score: {result['score']:.4f}")
                print(f"   Content: {result['content'][:200]}...")
                print(f"   Provenance: {result['provenance']}")
                print()
        else:
            # Stats mode
            stats = indexer.get_stats()
            print(f"\n📊 Collection Stats:")
            print(f"   Total entities: {stats['total_entities']}")
            print(f"   Collection: {stats['collection_name']}")
    
    asyncio.run(main())
