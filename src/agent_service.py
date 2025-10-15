"""
Agent Service - RAG-based Q&A with Provenance
Answers questions about code with commit-backed evidence
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncpg
from indexer_service import IndexerService
import openai

@dataclass
class AgentResponse:
    """Response from agent with provenance"""
    answer: str
    sources: List[Dict]
    provenance: List[Dict]
    confidence: float

class AgentService:
    """
    Agent Service - Intelligent Q&A with provenance
    
    Capabilities:
    - Answer "what changed?" queries
    - Explain code functionality
    - Compare versions
    - Provide commit-backed evidence
    """
    
    def __init__(self, indexer: IndexerService, db_url: str):
        self.indexer = indexer
        self.db_url = db_url
        self.pool = None
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        openai.api_key = self.openai_api_key
    
    async def init_db(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def classify_intent(self, question: str) -> str:
        """
        Classify user intent
        
        Types:
        - diff: "What changed between X and Y?"
        - explanation: "How does X work?"
        - usage: "How do I use X?"
        - breaking: "Is this a breaking change?"
        """
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['changed', 'difference', 'between', 'compare']):
            return 'diff'
        elif any(word in question_lower for word in ['breaking', 'deprecated']):
            return 'breaking'
        elif any(word in question_lower for word in ['how', 'use', 'example']):
            return 'usage'
        else:
            return 'explanation'
    
    async def get_commit_diff(self, repo_id: str, from_sha: str, to_sha: str) -> Optional[Dict]:
        """Get diff between two commits from database"""
        async with self.pool.acquire() as conn:
            # Get changelogs between commits
            rows = await conn.fetch("""
                SELECT * FROM changelogs
                WHERE repo_id = $1 
                AND commit_sha IN ($2, $3)
                ORDER BY timestamp DESC
            """, repo_id, from_sha, to_sha)
            
            return [dict(row) for row in rows]
    
    async def query(
        self, 
        question: str, 
        repo_id: Optional[str] = None,
        top_k: int = 5
    ) -> AgentResponse:
        """
        Answer a question with provenance
        
        Flow:
        1. Classify intent
        2. Retrieve relevant docs (vector search)
        3. Get additional context (diffs, etc.)
        4. Generate answer with LLM
        5. Return with citations
        """
        print(f"\n{'='*60}")
        print(f"❓ Question: {question}")
        print(f"{'='*60}\n")
        
        # 1. Classify intent
        intent = await self.classify_intent(question)
        print(f"🎯 Intent: {intent}")
        
        # 2. Retrieve relevant docs
        print(f"🔍 Searching vector DB...")
        results = await self.indexer.search(question, top_k=top_k, repo_id=repo_id)
        print(f"📊 Found {len(results)} relevant docs")
        
        # 3. Build context
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source {i}]")
            context_parts.append(f"Content: {result['content']}")
            context_parts.append(f"Commit: {result['provenance']['commit_sha']}")
            context_parts.append(f"Repo: {result['provenance']['repo_id']}")
            context_parts.append("")
        
        context = '\n'.join(context_parts)
        
        # 4. Generate answer with LLM
        print(f"🤖 Generating answer...")
        
        system_prompt = """You are a technical documentation assistant. 
Answer questions about code using the provided context.
Always cite your sources with commit SHAs and file paths.
Be concise and accurate."""
        
        user_prompt = f"""Question: {question}

Context from documentation:
{context}

Provide a clear answer with specific citations (commit SHAs, file paths).
Format citations as: [Source N: commit SHA]"""
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        answer = response['choices'][0]['message']['content']
        
        # 5. Format response
        agent_response = AgentResponse(
            answer=answer,
            sources=results,
            provenance=[r['provenance'] for r in results],
            confidence=1.0 - (results[0]['score'] if results else 1.0)
        )
        
        print(f"\n✅ Answer generated with {len(results)} sources")
        return agent_response
    
    async def compare_versions(
        self,
        repo_id: str,
        node_path: str,
        version1: str,
        version2: str
    ) -> AgentResponse:
        """
        Compare two versions of a doc node
        
        Useful for "What changed in X between v1 and v2?"
        """
        async with self.pool.acquire() as conn:
            # Get both versions
            v1 = await conn.fetchrow("""
                SELECT * FROM doc_nodes
                WHERE repo_id = $1 AND path = $2 AND version = $3
            """, repo_id, node_path, version1)
            
            v2 = await conn.fetchrow("""
                SELECT * FROM doc_nodes
                WHERE repo_id = $1 AND path = $2 AND version = $3
            """, repo_id, node_path, version2)
            
            if not v1 or not v2:
                return AgentResponse(
                    answer=f"Could not find both versions ({version1}, {version2})",
                    sources=[],
                    provenance=[],
                    confidence=0.0
                )
            
            # Get changelog between versions
            changelogs = await conn.fetch("""
                SELECT * FROM changelogs
                WHERE repo_id = $1
                AND timestamp BETWEEN 
                    (SELECT created_at FROM doc_nodes WHERE id = $2)
                    AND
                    (SELECT created_at FROM doc_nodes WHERE id = $3)
                ORDER BY timestamp ASC
            """, repo_id, v1['id'], v2['id'])
            
            # Build comparison
            changes = []
            for log in changelogs:
                changes.append(f"- {log['title']}: {log['summary']}")
            
            answer = f"""Changes in {node_path} from {version1} to {version2}:

{chr(10).join(changes)}

Version 1 (commit {v1['commit_sha'][:8]}):
{v1['content'].get('description', 'No description')}

Version 2 (commit {v2['commit_sha'][:8]}):
{v2['content'].get('description', 'No description')}"""
            
            return AgentResponse(
                answer=answer,
                sources=[dict(v1), dict(v2)],
                provenance=[
                    {'commit_sha': v1['commit_sha'], 'version': version1},
                    {'commit_sha': v2['commit_sha'], 'version': version2}
                ],
                confidence=1.0
            )


# CLI for testing
if __name__ == "__main__":
    import sys
    import asyncio
    
    async def main():
        # Initialize services
        indexer = IndexerService()
        indexer.connect()
        
        db_url = os.getenv("DATABASE_URL", "postgresql://localhost/lekhak_ai")
        agent = AgentService(indexer, db_url)
        await agent.init_db()
        
        # Get question from command line
        if len(sys.argv) < 2:
            print("Usage: python agent_service.py 'Your question here'")
            sys.exit(1)
        
        question = " ".join(sys.argv[1:])
        
        # Query agent
        response = await agent.query(question)
        
        # Print response
        print(f"\n{'='*60}")
        print(f"💡 Answer:")
        print(f"{'='*60}")
        print(response.answer)
        print(f"\n{'='*60}")
        print(f"📚 Sources ({len(response.sources)}):")
        print(f"{'='*60}")
        for i, source in enumerate(response.sources, 1):
            print(f"{i}. {source['provenance']}")
        print(f"\n🎯 Confidence: {response.confidence:.2%}")
    
    asyncio.run(main())
