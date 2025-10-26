"""
Canonical Documentation Model
Implements the hierarchical structure from the spec:
Product/Repo → SDK → Module → Feature → Function/Class
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class NodeType(Enum):
    """Types of documentation nodes"""
    PRODUCT = "product"
    SDK = "sdk"
    MODULE = "module"
    FEATURE = "feature"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ENDPOINT = "endpoint"


@dataclass
class Example:
    """Code example with metadata"""
    title: str
    code: str
    language: str
    description: Optional[str] = None


@dataclass
class VersionInfo:
    """Version history for a node"""
    version: str
    commit_sha: str
    timestamp: datetime
    changes: str
    author: str


@dataclass
class Reference:
    """Cross-reference to another node or external resource"""
    title: str
    target_id: Optional[str] = None  # Internal node ID
    url: Optional[str] = None  # External URL
    type: str = "internal"  # internal | external


@dataclass
class Provenance:
    """Provenance metadata for tracking source"""
    commit_sha: str
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class DocNode:
    """
    Canonical documentation node
    Represents any level in the hierarchy
    """
    # Core identity
    id: str
    title: str
    type: NodeType
    
    # Hierarchy
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    path: str = ""  # File system path or logical path
    
    # Content
    description: str = ""
    signature: Optional[str] = None  # For functions/methods
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    
    # Examples and references
    examples: List[Example] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    
    # Versioning
    versions: List[VersionInfo] = field(default_factory=list)
    current_version: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    visibility: str = "public"  # public | private | internal
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Provenance
    provenance: Optional[Provenance] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "path": self.path,
            "description": self.description,
            "signature": self.signature,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "examples": [
                {
                    "title": ex.title,
                    "code": ex.code,
                    "language": ex.language,
                    "description": ex.description
                }
                for ex in self.examples
            ],
            "references": [
                {
                    "title": ref.title,
                    "target_id": ref.target_id,
                    "url": ref.url,
                    "type": ref.type
                }
                for ref in self.references
            ],
            "versions": [
                {
                    "version": v.version,
                    "commit_sha": v.commit_sha,
                    "timestamp": v.timestamp.isoformat(),
                    "changes": v.changes,
                    "author": v.author
                }
                for v in self.versions
            ],
            "current_version": self.current_version,
            "tags": self.tags,
            "visibility": self.visibility,
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "provenance": {
                "commit_sha": self.provenance.commit_sha,
                "file_path": self.provenance.file_path,
                "line_start": self.provenance.line_start,
                "line_end": self.provenance.line_end,
                "author": self.provenance.author,
                "timestamp": self.provenance.timestamp.isoformat() if self.provenance.timestamp else None
            } if self.provenance else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocNode':
        """Create from dictionary"""
        # Parse examples
        examples = [
            Example(
                title=ex["title"],
                code=ex["code"],
                language=ex["language"],
                description=ex.get("description")
            )
            for ex in data.get("examples", [])
        ]
        
        # Parse references
        references = [
            Reference(
                title=ref["title"],
                target_id=ref.get("target_id"),
                url=ref.get("url"),
                type=ref.get("type", "internal")
            )
            for ref in data.get("references", [])
        ]
        
        # Parse versions
        versions = [
            VersionInfo(
                version=v["version"],
                commit_sha=v["commit_sha"],
                timestamp=datetime.fromisoformat(v["timestamp"]),
                changes=v["changes"],
                author=v["author"]
            )
            for v in data.get("versions", [])
        ]
        
        # Parse provenance
        provenance = None
        if data.get("provenance"):
            p = data["provenance"]
            provenance = Provenance(
                commit_sha=p["commit_sha"],
                file_path=p["file_path"],
                line_start=p.get("line_start"),
                line_end=p.get("line_end"),
                author=p.get("author"),
                timestamp=datetime.fromisoformat(p["timestamp"]) if p.get("timestamp") else None
            )
        
        return cls(
            id=data["id"],
            title=data["title"],
            type=NodeType(data["type"]),
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            path=data.get("path", ""),
            description=data.get("description", ""),
            signature=data.get("signature"),
            parameters=data.get("parameters", []),
            return_type=data.get("return_type"),
            examples=examples,
            references=references,
            versions=versions,
            current_version=data.get("current_version"),
            tags=data.get("tags", []),
            visibility=data.get("visibility", "public"),
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            provenance=provenance,
            metadata=data.get("metadata", {})
        )


@dataclass
class DocumentationTree:
    """
    Complete documentation tree for a repository
    """
    repo_id: str
    root_node_id: str
    nodes: Dict[str, DocNode] = field(default_factory=dict)
    commit_sha: str = ""
    version: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_node(self, node: DocNode):
        """Add a node to the tree"""
        self.nodes[node.id] = node
        
        # Update parent's children list
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.children_ids:
                parent.children_ids.append(node.id)
    
    def get_node(self, node_id: str) -> Optional[DocNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)
    
    def get_children(self, node_id: str) -> List[DocNode]:
        """Get all children of a node"""
        node = self.get_node(node_id)
        if not node:
            return []
        return [self.nodes[child_id] for child_id in node.children_ids if child_id in self.nodes]
    
    def get_breadcrumb(self, node_id: str) -> List[DocNode]:
        """Get breadcrumb trail from root to node"""
        breadcrumb = []
        current_id = node_id
        
        while current_id:
            node = self.get_node(current_id)
            if not node:
                break
            breadcrumb.insert(0, node)
            current_id = node.parent_id
        
        return breadcrumb
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "repo_id": self.repo_id,
            "root_node_id": self.root_node_id,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "commit_sha": self.commit_sha,
            "version": self.version,
            "created_at": self.created_at.isoformat()
        }


# Helper functions

def create_product_node(repo_id: str, repo_name: str, description: str = "") -> DocNode:
    """Create a product/repo root node"""
    return DocNode(
        id=f"product_{repo_id}",
        title=repo_name,
        type=NodeType.PRODUCT,
        description=description,
        path="/"
    )


def create_sdk_node(sdk_name: str, parent_id: str, description: str = "") -> DocNode:
    """Create an SDK node"""
    return DocNode(
        id=f"sdk_{sdk_name}",
        title=sdk_name,
        type=NodeType.SDK,
        parent_id=parent_id,
        description=description
    )


def create_module_node(module_name: str, parent_id: str, path: str, description: str = "") -> DocNode:
    """Create a module node"""
    return DocNode(
        id=f"module_{module_name}_{parent_id}",
        title=module_name,
        type=NodeType.MODULE,
        parent_id=parent_id,
        path=path,
        description=description
    )


def create_function_node(
    func_name: str,
    parent_id: str,
    signature: str,
    description: str = "",
    parameters: List[Dict] = None,
    return_type: str = None,
    provenance: Provenance = None
) -> DocNode:
    """Create a function node"""
    return DocNode(
        id=f"func_{func_name}_{parent_id}",
        title=func_name,
        type=NodeType.FUNCTION,
        parent_id=parent_id,
        signature=signature,
        description=description,
        parameters=parameters or [],
        return_type=return_type,
        provenance=provenance
    )
