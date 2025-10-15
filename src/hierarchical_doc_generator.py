"""
Hierarchical Documentation Generator
Builds deep tree structure: Repo → SDK → Module → Feature → Function

This replaces flat documentation with a rich, navigable hierarchy.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import asyncpg
from datetime import datetime
from universal_code_parser import UniversalCodeParser

@dataclass
class DocNode:
    """
    Represents a node in the documentation tree
    
    Types:
    - repo: Root (entire repository)
    - sdk: Top-level SDK/package
    - module: Subdirectory/module
    - feature: Logical grouping of functions
    - function: Individual function
    - class: Class definition
    - interface: TypeScript interface
    """
    id: str
    type: str  # repo|sdk|module|feature|function|class|interface
    title: str
    slug: str
    path: str
    parent_id: Optional[str]
    depth: int
    position: int
    commit_sha: str
    version: Optional[str]
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    children: List['DocNode']
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['children'] = [child.to_dict() for child in self.children]
        return data


# Use UniversalCodeParser (supports ALL languages)
CodeParser = UniversalCodeParser


class HierarchicalDocGenerator:
    """
    Generate hierarchical documentation structure
    
    Flow:
    1. Analyze repo structure
    2. Detect SDKs (top-level packages)
    3. Find modules (subdirectories)
    4. Parse code files
    5. Group functions into features
    6. Build tree structure
    7. Generate descriptions with LLM
    8. Store in database
    """
    
    def __init__(self, repo_dir: Path, repo_id: str, commit_sha: str, db_url: str):
        self.repo_dir = repo_dir
        self.repo_id = repo_id
        self.commit_sha = commit_sha
        self.db_url = db_url
        self.pool = None
        self.node_counter = 0
    
    async def init_db(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
    
    def generate_id(self) -> str:
        """Generate unique node ID"""
        self.node_counter += 1
        return f"{self.repo_id}_{self.commit_sha[:8]}_{self.node_counter}"
    
    def create_slug(self, title: str) -> str:
        """Create URL-friendly slug"""
        return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    
    async def analyze_repo(self) -> DocNode:
        """
        Analyze repository and build complete tree
        
        Returns: Root node with full hierarchy
        """
        print(f"\n{'='*60}")
        print(f"📊 Analyzing repository: {self.repo_id}")
        print(f"   Commit: {self.commit_sha[:8]}")
        print(f"   Path: {self.repo_dir}")
        print(f"{'='*60}\n")
        
        # Create root node
        root = DocNode(
            id=self.generate_id(),
            type='repo',
            title=self.repo_id.split('/')[-1],
            slug=self.create_slug(self.repo_id),
            path='/',
            parent_id=None,
            depth=0,
            position=0,
            commit_sha=self.commit_sha,
            version=None,
            content={'description': f'Documentation for {self.repo_id}'},
            metadata={'repo_id': self.repo_id, 'commit_sha': self.commit_sha},
            children=[]
        )
        
        # Find SDKs (top-level directories with code)
        sdks = self.find_sdks()
        print(f"📦 Found {len(sdks)} SDKs: {[s.name for s in sdks]}")
        
        for idx, sdk_dir in enumerate(sdks):
            sdk_node = await self.analyze_sdk(sdk_dir, root.id, idx)
            root.children.append(sdk_node)
        
        print(f"\n✅ Analysis complete! Generated {self.node_counter} nodes")
        return root
    
    def find_sdks(self) -> List[Path]:
        """
        Find SDK directories (top-level packages)
        
        Heuristics:
        - Has __init__.py (Python) or index.ts (TypeScript)
        - Has package.json or setup.py
        - Contains code files
        """
        sdks = []
        
        for item in self.repo_dir.iterdir():
            if not item.is_dir():
                continue
            
            # Skip hidden, node_modules, venv, etc.
            if item.name.startswith('.') or item.name in ['node_modules', 'venv', '__pycache__', 'dist', 'build']:
                continue
            
            # Check for SDK indicators
            has_init = (item / '__init__.py').exists()
            has_index = (item / 'index.ts').exists() or (item / 'index.tsx').exists()
            has_package = (item / 'package.json').exists()
            has_setup = (item / 'setup.py').exists()
            
            # Check for code files
            has_code = any(item.glob('*.py')) or any(item.glob('*.ts')) or any(item.glob('*.tsx'))
            
            if (has_init or has_index or has_package or has_setup) and has_code:
                sdks.append(item)
        
        return sdks
    
    async def analyze_sdk(self, sdk_dir: Path, parent_id: str, position: int) -> DocNode:
        """Analyze SDK and build module tree"""
        print(f"  📦 Analyzing SDK: {sdk_dir.name}")
        
        sdk_node = DocNode(
            id=self.generate_id(),
            type='sdk',
            title=sdk_dir.name,
            slug=self.create_slug(sdk_dir.name),
            path=f'/{sdk_dir.name}',
            parent_id=parent_id,
            depth=1,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={'description': f'SDK: {sdk_dir.name}'},
            metadata={'directory': str(sdk_dir)},
            children=[]
        )
        
        # Find modules (subdirectories)
        modules = [d for d in sdk_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        for idx, module_dir in enumerate(modules):
            module_node = await self.analyze_module(module_dir, sdk_node.id, idx, sdk_node.path)
            sdk_node.children.append(module_node)
        
        # Also parse files directly in SDK directory (all supported languages)
        files = []
        for ext in UniversalCodeParser.LANGUAGE_MAP.keys():
            files.extend(sdk_dir.glob(f'*{ext}'))
        
        if files:
            direct_module = await self.analyze_files(files, sdk_node.id, len(modules), sdk_node.path, sdk_dir.name)
            sdk_node.children.append(direct_module)
        
        return sdk_node
    
    async def analyze_module(self, module_dir: Path, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Analyze module and extract features"""
        print(f"    📂 Analyzing module: {module_dir.name}")
        
        module_node = DocNode(
            id=self.generate_id(),
            type='module',
            title=module_dir.name,
            slug=self.create_slug(module_dir.name),
            path=f'{parent_path}/{module_dir.name}',
            parent_id=parent_id,
            depth=2,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={'description': f'Module: {module_dir.name}'},
            metadata={'directory': str(module_dir)},
            children=[]
        )
        
        # Parse all code files in module (all supported languages)
        files = []
        for ext in UniversalCodeParser.LANGUAGE_MAP.keys():
            files.extend(module_dir.glob(f'*{ext}'))
        
        if files:
            all_items = []
            for file in files:
                items = CodeParser.parse_file(file)
                # Convert CodeItem to dict
                all_items.extend([{
                    'type': item.type,
                    'name': item.name,
                    'signature': item.signature,
                    'docstring': item.docstring,
                    'file': item.file,
                    'line_start': item.line_start,
                    'line_end': item.line_end,
                    'language': item.language,
                    **item.metadata
                } for item in items])
            
            # Group into features
            features = self.group_into_features(all_items)
            
            for idx, (feature_name, items) in enumerate(features.items()):
                feature_node = self.create_feature_node(
                    feature_name, items, module_node.id, idx, module_node.path
                )
                module_node.children.append(feature_node)
        
        return module_node
    
    async def analyze_files(self, files: List[Path], parent_id: str, position: int, parent_path: str, name: str) -> DocNode:
        """Analyze files directly (not in subdirectory)"""
        module_node = DocNode(
            id=self.generate_id(),
            type='module',
            title=name,
            slug=self.create_slug(name),
            path=f'{parent_path}/{name}',
            parent_id=parent_id,
            depth=2,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={'description': f'Module: {name}'},
            metadata={},
            children=[]
        )
        
        all_items = []
        for file in files:
            items = CodeParser.parse_file(file)
            all_items.extend(items)
        
        # Group into features
        features = self.group_into_features(all_items)
        
        for idx, (feature_name, items) in enumerate(features.items()):
            feature_node = self.create_feature_node(
                feature_name, items, module_node.id, idx, module_node.path
            )
            module_node.children.append(feature_node)
        
        return module_node
    
    def group_into_features(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group functions/classes into logical features
        
        Strategies:
        1. By prefix (create*, update*, delete*)
        2. By file name
        3. By class membership
        """
        features = {}
        
        for item in items:
            if item['type'] == 'function':
                # Group by prefix
                name = item['name']
                if '_' in name:
                    prefix = name.split('_')[0]
                else:
                    # CamelCase: get first word
                    prefix = re.sub(r'([A-Z][a-z]+)', r'\1_', name).split('_')[0]
                
                feature_name = prefix.capitalize() if prefix else 'General'
                
            elif item['type'] == 'class':
                # Each class is its own feature
                feature_name = item['name']
            
            else:
                feature_name = 'General'
            
            if feature_name not in features:
                features[feature_name] = []
            features[feature_name].append(item)
        
        return features
    
    def create_feature_node(
        self, 
        feature_name: str, 
        items: List[Dict], 
        parent_id: str, 
        position: int,
        parent_path: str
    ) -> DocNode:
        """Create feature node with function/class children"""
        print(f"      🎯 Feature: {feature_name} ({len(items)} items)")
        
        feature_node = DocNode(
            id=self.generate_id(),
            type='feature',
            title=feature_name,
            slug=self.create_slug(feature_name),
            path=f'{parent_path}/{self.create_slug(feature_name)}',
            parent_id=parent_id,
            depth=3,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={'description': f'Feature: {feature_name}'},
            metadata={'item_count': len(items)},
            children=[]
        )
        
        for idx, item in enumerate(items):
            if item['type'] == 'function':
                func_node = self.create_function_node(item, feature_node.id, idx, feature_node.path)
                feature_node.children.append(func_node)
            elif item['type'] == 'class':
                class_node = self.create_class_node(item, feature_node.id, idx, feature_node.path)
                feature_node.children.append(class_node)
        
        return feature_node
    
    def create_function_node(self, func: Dict, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Create doc node for function"""
        # Build signature
        if 'params' in func:  # TypeScript
            signature = f"{'async ' if func.get('is_async') else ''}function {func['name']}({func['params']}): {func.get('return_type', 'void')}"
        else:  # Python
            args_str = ', '.join(func.get('args', []))
            signature = f"{'async ' if func.get('is_async') else ''}def {func['name']}({args_str})"
        
        return DocNode(
            id=self.generate_id(),
            type='function',
            title=func['name'],
            slug=self.create_slug(func['name']),
            path=f"{parent_path}/{self.create_slug(func['name'])}",
            parent_id=parent_id,
            depth=4,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={
                'signature': signature,
                'description': func.get('docstring', ''),
                'parameters': [],  # TODO: Parse from signature
                'returns': {},
                'examples': [],
                'related': []
            },
            metadata={
                'file': func.get('file', ''),
                'line_start': func.get('line_start'),
                'line_end': func.get('line_end'),
                'is_async': func.get('is_async', False)
            },
            children=[]
        )
    
    def create_class_node(self, cls: Dict, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Create doc node for class"""
        return DocNode(
            id=self.generate_id(),
            type='class',
            title=cls['name'],
            slug=self.create_slug(cls['name']),
            path=f"{parent_path}/{self.create_slug(cls['name'])}",
            parent_id=parent_id,
            depth=4,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={
                'description': cls.get('docstring', ''),
                'methods': cls.get('methods', []),
                'properties': cls.get('properties', ''),
                'extends': cls.get('extends') or cls.get('bases', [])
            },
            metadata={
                'file': cls.get('file', ''),
                'line_start': cls.get('line_start'),
                'line_end': cls.get('line_end')
            },
            children=[]
        )
    
    async def save_tree(self, node: DocNode):
        """
        Save node tree to database (recursive)
        
        Stores in doc_nodes table with parent-child relationships
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO doc_nodes (
                    id, repo_id, type, title, slug, path, parent_id, depth, position,
                    commit_sha, version, content, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
                ON CONFLICT (repo_id, path, commit_sha) DO UPDATE
                SET content = EXCLUDED.content, metadata = EXCLUDED.metadata, updated_at = NOW()
            """,
                node.id, self.repo_id, node.type, node.title, node.slug, node.path,
                node.parent_id, node.depth, node.position, node.commit_sha, node.version,
                json.dumps(node.content), json.dumps(node.metadata)
            )
        
        # Recursively save children
        for child in node.children:
            await self.save_tree(child)
    
    async def generate(self) -> DocNode:
        """
        Main entry point: Generate complete hierarchical documentation
        
        Returns: Root node with full tree
        """
        await self.init_db()
        
        # Analyze repository
        root = await self.analyze_repo()
        
        # Save to database
        print(f"\n💾 Saving to database...")
        await self.save_tree(root)
        print(f"✅ Saved {self.node_counter} nodes")
        
        # Close database
        await self.pool.close()
        
        return root


# CLI for testing
if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python hierarchical_doc_generator.py <repo_dir> <repo_id> <commit_sha>")
        sys.exit(1)
    
    repo_dir = Path(sys.argv[1])
    repo_id = sys.argv[2]
    commit_sha = sys.argv[3]
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/lekhak_ai")
    
    async def main():
        generator = HierarchicalDocGenerator(repo_dir, repo_id, commit_sha, db_url)
        root = await generator.generate()
        
        # Print tree
        print("\n" + "="*60)
        print("📊 Generated Tree Structure:")
        print("="*60)
        print(json.dumps(root.to_dict(), indent=2))
    
    asyncio.run(main())
