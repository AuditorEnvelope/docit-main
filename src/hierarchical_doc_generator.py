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
from llm_provider_v2 import get_rotator

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
    
    def __init__(self, repo_dir: Path, repo_id: str, commit_sha: str, db_url: str, changed_files: List[str] = None):
        self.repo_dir = repo_dir
        self.repo_id = repo_id
        self.commit_sha = commit_sha
        self.db_url = db_url
        self.pool = None
        self.node_counter = 0
        self.llm_rotator = None  # Initialize LLM for descriptions
        self.changed_files = set(changed_files or [])  # Track changed files for smart caching
        self.description_cache = {}  # Cache for reused descriptions
        self.llm_calls_saved = 0  # Track optimization
    
    async def init_db(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
        
        # Initialize LLM for AI-generated descriptions
        try:
            self.llm_rotator = get_rotator()
            print("✅ LLM initialized for AI descriptions")
        except Exception as e:
            print(f"⚠️  LLM initialization failed: {e}")
            self.llm_rotator = None
        
        # Load previous descriptions for unchanged files
        await self.load_description_cache()
    
    def generate_id(self) -> str:
        """Generate unique node ID"""
        self.node_counter += 1
        return f"{self.repo_id}_{self.commit_sha[:8]}_{self.node_counter}"
    
    def create_slug(self, title: str) -> str:
        """Create URL-friendly slug"""
        return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    
    async def load_description_cache(self):
        """Load descriptions from previous commit for unchanged files"""
        try:
            async with self.pool.acquire() as conn:
                # Get previous commit for this repo
                prev_commit = await conn.fetchval("""
                    SELECT commit_sha FROM doc_nodes
                    WHERE repo_id = $1 AND commit_sha != $2
                    ORDER BY created_at DESC
                    LIMIT 1
                """, self.repo_id, self.commit_sha)
                
                if not prev_commit:
                    print("ℹ️  No previous commit found - full generation")
                    return
                
                # Load all nodes from previous commit
                nodes = await conn.fetch("""
                    SELECT path, type, content, metadata
                    FROM doc_nodes
                    WHERE repo_id = $1 AND commit_sha = $2
                """, self.repo_id, prev_commit)
                
                # Cache ALL descriptions (repo, SDK, modules, features, files, functions)
                for node in nodes:
                    path = node['path']
                    node_type = node['type']
                    
                    # Create the same cache key format used in generate_description
                    if node_type in ['repo', 'sdk', 'module', 'feature']:
                        cache_key = f"{self.repo_id}:{prev_commit}:{node_type}:{path}"
                    else:
                        cache_key = f"{node_type}:{path}"
                    
                    # For structural nodes (repo, SDK, module, feature), always cache
                    # For code nodes (file, function, class), check if file changed
                    should_cache = True
                    
                    if node_type in ['file', 'function', 'class']:
                        # Extract file path from metadata
                        metadata = node.get('metadata', {})
                        if isinstance(metadata, str):
                            import json
                            metadata = json.loads(metadata)
                        
                        file_path = metadata.get('file_path', '')
                        
                        # Only cache if file wasn't changed
                        if file_path and any(changed in file_path for changed in self.changed_files):
                            should_cache = False
                    
                    if should_cache:
                        content = node.get('content', {})
                        if isinstance(content, str):
                            import json
                            content = json.loads(content)
                        
                        description = content.get('description', '')
                        if description:
                            self.description_cache[cache_key] = description
                
                print(f"✅ Loaded {len(self.description_cache)} cached descriptions from previous commit")
                print(f"📝 Changed files: {len(self.changed_files)}")
                
        except Exception as e:
            print(f"⚠️  Failed to load description cache: {e}")
            self.description_cache = {}
    
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
            content={'description': await self.generate_description('repo', self.repo_id, {'type': 'repository', 'path': '/'})},  
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
        if self.llm_calls_saved > 0:
            print(f"💾 Optimization: Reused {self.llm_calls_saved} cached descriptions (saved ~{self.llm_calls_saved * 2}s)")
        return root
    
    async def store_tree(self, root_node: DocNode):
        """
        Store the entire tree structure in the database
        
        This recursively stores all nodes in the tree, maintaining parent-child relationships.
        """
        print(f"\n💾 Storing tree structure in database...")
        
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call init_db() first.")
        
        # Map of node.id (string) -> database UUID
        self.id_map = {}
        
        # Store nodes recursively
        await self._store_node_recursive(root_node, parent_uuid=None)
        
        print(f"✅ Successfully stored {self.node_counter} nodes in database")
    
    async def _store_node_recursive(self, node: DocNode, parent_uuid=None):
        """Recursively store a node and its children"""
        async with self.pool.acquire() as conn:
            # Insert or update the node and get the UUID
            result = await conn.fetchrow("""
                INSERT INTO doc_nodes (
                    repo_id, type, title, slug, path,
                    parent_id, depth, position, commit_sha, version,
                    content, metadata, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12, NOW(), NOW()
                )
                ON CONFLICT (repo_id, path, commit_sha) 
                DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id
            """, 
                self.repo_id,           # $1
                node.type,              # $2
                node.title,             # $3
                node.slug,              # $4
                node.path,              # $5
                parent_uuid,            # $6 - Use the actual UUID from parent
                node.depth,             # $7
                node.position,          # $8
                self.commit_sha,        # $9
                node.version,           # $10
                json.dumps(node.content),   # $11
                json.dumps(node.metadata)   # $12
            )
            
            # Store the database UUID for this node
            node_uuid = result['id']
            self.id_map[node.id] = node_uuid
        
        # Recursively store children with this node's UUID as parent
        for child in node.children:
            await self._store_node_recursive(child, parent_uuid=node_uuid)
    
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
            content={'description': await self.generate_description('sdk', sdk_dir.name, {'type': 'sdk', 'path': str(sdk_dir)})},  
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
            files.extend(sdk_dir.glob(f'*{ext}'))  # Only direct files, not recursive here
        
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
            content={'description': await self.generate_description('module', module_dir.name, {'type': 'module', 'path': str(module_dir)})},  
            metadata={'directory': str(module_dir)},
            children=[]
        )
        
        # BETTER APPROACH: Analyze subdirectories as features (logical grouping)
        subdirs = [d for d in module_dir.iterdir() if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('__')]
        
        if subdirs:
            # Has subdirectories - treat each as a feature
            print(f"      📁 Found {len(subdirs)} subdirectories")
            for idx, subdir in enumerate(subdirs):
                feature_node = await self.analyze_directory_as_feature(subdir, module_node.id, idx, module_node.path)
                module_node.children.append(feature_node)
        else:
            # No subdirectories - parse files directly
            files = []
            for ext in UniversalCodeParser.LANGUAGE_MAP.keys():
                files.extend(module_dir.glob(f'*{ext}'))  # Only direct files
            
            if files:
                print(f"      📄 Found {len(files)} files in {module_dir.name}")
                for idx, file in enumerate(files):
                    file_node = await self.analyze_file_as_node(file, module_node.id, idx, module_node.path)
                    if file_node:
                        module_node.children.append(file_node)
        
        return module_node
    
    async def analyze_directory_as_feature(self, dir_path: Path, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Analyze a directory as a feature (e.g., app/, components/, lib/)"""
        print(f"        📂 Feature directory: {dir_path.name}")
        
        feature_node = DocNode(
            id=self.generate_id(),
            type='feature',
            title=dir_path.name,
            slug=self.create_slug(dir_path.name),
            path=f'{parent_path}/{dir_path.name}',
            parent_id=parent_id,
            depth=3,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={'description': await self.generate_description('feature', dir_path.name, {'type': 'directory', 'path': str(dir_path)})},  
            metadata={'directory': str(dir_path)},
            children=[]
        )
        
        # Parse all files in this directory (recursively)
        files = []
        for ext in UniversalCodeParser.LANGUAGE_MAP.keys():
            files.extend(dir_path.rglob(f'*{ext}'))
        
        if files:
            print(f"          📄 {len(files)} files in {dir_path.name}")
            for idx, file in enumerate(files[:20]):  # Limit to 20 files per directory
                file_node = await self.analyze_file_as_node(file, feature_node.id, idx, feature_node.path)
                if file_node:
                    feature_node.children.append(file_node)
        
        return feature_node
    
    async def analyze_file_as_node(self, file_path: Path, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Analyze a single file as a node"""
        try:
            items = CodeParser.parse_file(file_path)
            
            # Get relative path from parent
            file_name = file_path.name
            
            # Create file node
            file_node = DocNode(
                id=self.generate_id(),
                type='file',
                title=file_name,
                slug=self.create_slug(file_name),
                path=f'{parent_path}/{file_name}',
                parent_id=parent_id,
                depth=4,
                position=position,
                commit_sha=self.commit_sha,
                version=None,
                content={
                    'description': await self.generate_description('file', file_name, {
                        'type': 'file',
                        'functions': [item.name for item in items if item.type == 'function'],
                        'classes': [item.name for item in items if item.type == 'class'],
                        'item_count': len(items)
                    }),
                    'functions': [item.name for item in items if item.type == 'function'],
                    'classes': [item.name for item in items if item.type == 'class'],
                    'item_count': len(items)
                },
                metadata={'file_path': str(file_path)},
                children=[]
            )
            
            # Add top-level functions/classes as children (limit to 10)
            for idx, item in enumerate(items[:10]):
                if item.type == 'function':
                    func_node = await self.create_function_node_from_item(item, file_node.id, idx, file_node.path)
                    file_node.children.append(func_node)
                elif item.type == 'class':
                    class_node = await self.create_class_node_from_item(item, file_node.id, idx, file_node.path)
                    file_node.children.append(class_node)
            
            return file_node
        except Exception as e:
            print(f"          ⚠️  Error parsing {file_path.name}: {e}")
            return None
    
    async def create_function_node_from_item(self, item, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Create function node from CodeItem"""
        return DocNode(
            id=self.generate_id(),
            type='function',
            title=item.name,
            slug=self.create_slug(item.name),
            path=f"{parent_path}/{self.create_slug(item.name)}",
            parent_id=parent_id,
            depth=5,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={
                'signature': item.signature,
                'description': item.docstring or await self.generate_description('function', item.name, {
                    'signature': item.signature,
                    'type': 'function'
                }),
                'file': item.file,
                'line_start': item.line_start,
                'line_end': item.line_end,
                'parameters': self.extract_parameters(item.signature),
                'return_type': self.extract_return_type(item.signature)
            },
            metadata={'language': item.language},
            children=[]
        )
    
    async def create_class_node_from_item(self, item, parent_id: str, position: int, parent_path: str) -> DocNode:
        """Create class node from CodeItem"""
        return DocNode(
            id=self.generate_id(),
            type='class',
            title=item.name,
            slug=self.create_slug(item.name),
            path=f"{parent_path}/{self.create_slug(item.name)}",
            parent_id=parent_id,
            depth=5,
            position=position,
            commit_sha=self.commit_sha,
            version=None,
            content={
                'description': item.docstring or await self.generate_description('class', item.name, {
                    'type': 'class'
                }),
                'file': item.file,
                'line_start': item.line_start,
                'line_end': item.line_end
            },
            metadata={'language': item.language},
            children=[]
        )
    
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
            content={'description': await self.generate_description('module', name, {'type': 'module', 'path': f'{parent_path}/{name}'})},  
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
            feature_node = await self.create_feature_node(
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
    
    async def create_feature_node(
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
            content={'description': await self.generate_description('feature', feature_name, {'type': 'feature', 'item_count': len(items)})},  
            metadata={'item_count': len(items)},
            children=[]
        )
        
        for idx, item in enumerate(items):
            if item['type'] == 'function':
                func_node = await self.create_function_node(item, feature_node.id, idx, feature_node.path)
                feature_node.children.append(func_node)
            elif item['type'] == 'class':
                class_node = await self.create_class_node(item, feature_node.id, idx, feature_node.path)
                feature_node.children.append(class_node)
        
        return feature_node
    
    async def create_function_node(self, func: Dict, parent_id: str, position: int, parent_path: str) -> DocNode:
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
                'description': func.get('docstring', '') or await self.generate_description('function', func['name'], {
                    'signature': signature,
                    'type': 'function'
                }),
                'parameters': self.extract_parameters(signature),
                'return_type': self.extract_return_type(signature),
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
    
    async def create_class_node(self, cls: Dict, parent_id: str, position: int, parent_path: str) -> DocNode:
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
                'description': cls.get('docstring', '') or await self.generate_description('class', cls['name'], {
                    'type': 'class',
                    'methods': cls.get('methods', []),
                    'extends': cls.get('extends') or cls.get('bases', [])
                }),
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
    
    async def generate_description(self, node_type: str, name: str, context: Dict) -> str:
        """Generate AI description for a node (with smart caching)"""
        # Create cache key - use a stable identifier based on repo, commit, and logical path
        file_path = context.get('file_path', context.get('path', ''))

        # For structural nodes, create a more stable cache key
        if node_type in ['repo', 'sdk', 'module', 'feature']:
            # Use repo_id + commit_sha + logical path as cache key
            cache_key = f"{self.repo_id}:{self.commit_sha}:{node_type}:{file_path or name}"
        else:
            # For code nodes, use the file path
            cache_key = f"{node_type}:{file_path or name}"

        # Check cache first
        if cache_key in self.description_cache:
            self.llm_calls_saved += 1
            if self.llm_calls_saved % 10 == 0:  # Log every 10 saves
                print(f"💾 Reused {self.llm_calls_saved} cached descriptions")
            return self.description_cache[cache_key]

        # For structural nodes (repo, SDK, module, feature) - always regenerate if not cached
        # For code nodes (file, function, class) - check if file was changed
        if node_type in ['file', 'function', 'class']:
            # Check if this file was changed - if not, use fallback (don't waste LLM calls)
            if file_path and self.changed_files:
                is_changed = any(changed in str(file_path) for changed in self.changed_files)
                if not is_changed:
                    # File unchanged but not in cache - use simple fallback
                    return self._fallback_description(node_type, name, context)

        # Generate new description with LLM
        if not self.llm_rotator:
            return self._fallback_description(node_type, name, context)

        try:
            prompt = self._create_description_prompt(node_type, name, context)
            description = self.llm_rotator.generate_with_rotation(prompt, max_attempts=2)

            if description:
                # Clean up the description (remove markdown, etc.)
                description = description.strip()
                if description.startswith('#'):
                    description = '\n'.join(description.split('\n')[1:]).strip()
                description = description[:500]  # Limit length

                # Cache for future use
                self.description_cache[cache_key] = description
                return description
            else:
                return self._fallback_description(node_type, name, context)
        except Exception as e:
            print(f"⚠️  LLM description failed for {name}: {e}")
            return self._fallback_description(node_type, name, context)
    
    def _create_description_prompt(self, node_type: str, name: str, context: Dict) -> str:
        """Create prompt for LLM description generation"""
        if node_type == 'repo':
            return f"""Describe this repository in 1-2 sentences: {name}
Be concise and technical."""
        elif node_type == 'sdk':
            return f"""Describe this SDK/package in 1 sentence: {name}
Focus on its purpose."""
        elif node_type == 'module':
            return f"""Describe this module in 1 sentence: {name}
Explain what it contains."""
        elif node_type == 'feature':
            items = context.get('item_count', 0)
            return f"""Describe this feature directory in 1 sentence: {name}
It contains {items} code items."""
        elif node_type == 'file':
            funcs = context.get('functions', [])
            classes = context.get('classes', [])
            return f"""Describe this code file in 1 sentence: {name}
Functions: {', '.join(funcs[:3])}
Classes: {', '.join(classes[:3])}"""
        elif node_type == 'function':
            sig = context.get('signature', '')
            return f"""Describe what this function does in 1 sentence: {sig}
Be specific about its purpose."""
        elif node_type == 'class':
            methods = context.get('methods', [])
            return f"""Describe this class in 1 sentence: {name}
Methods: {', '.join([m.get('name', '') for m in methods[:3]])}"""
        else:
            return f"Describe {name} in 1 sentence."
    
    def _fallback_description(self, node_type: str, name: str, context: Dict) -> str:
        """Fallback description when LLM is unavailable"""
        if node_type == 'repo':
            return f"Documentation for {name} repository"
        elif node_type == 'sdk':
            return f"SDK: {name}"
        elif node_type == 'module':
            return f"Module: {name}"
        elif node_type == 'feature':
            return f"Feature: {name}"
        elif node_type == 'file':
            return f"File: {name}"
        elif node_type == 'function':
            return f"Function: {name}"
        elif node_type == 'class':
            return f"Class: {name}"
        else:
            return f"{node_type.capitalize()}: {name}"
    
    def extract_parameters(self, signature: str) -> List[Dict]:
        """Extract parameters from function signature"""
        try:
            # Match content between parentheses
            match = re.search(r'\(([^)]*)\)', signature)
            if not match:
                return []
            
            params_str = match.group(1).strip()
            if not params_str or params_str in ['', 'self', 'cls']:
                return []
            
            params = []
            for param in params_str.split(','):
                param = param.strip()
                if not param or param in ['self', 'cls']:
                    continue
                
                # Parse param: name, type, default
                parts = param.split(':')
                name = parts[0].strip()
                
                param_type = None
                default = None
                
                if len(parts) > 1:
                    type_and_default = parts[1].strip()
                    if '=' in type_and_default:
                        type_part, default = type_and_default.split('=', 1)
                        param_type = type_part.strip()
                        default = default.strip()
                    else:
                        param_type = type_and_default
                elif '=' in name:
                    name, default = name.split('=', 1)
                    name = name.strip()
                    default = default.strip()
                
                params.append({
                    'name': name,
                    'type': param_type,
                    'default': default
                })
            
            return params
        except Exception as e:
            print(f"⚠️  Error extracting parameters: {e}")
            return []
    
    def extract_return_type(self, signature: str) -> Optional[str]:
        """Extract return type from function signature"""
        try:
            # Python: def func() -> ReturnType:
            match = re.search(r'->\s*([^:]+)', signature)
            if match:
                return match.group(1).strip()
            
            # TypeScript: function func(): ReturnType
            match = re.search(r'\)\s*:\s*([^{;]+)', signature)
            if match:
                return match.group(1).strip()
            
            return None
        except Exception:
            return None
    
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
