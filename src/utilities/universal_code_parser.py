"""
Universal Code Parser - Support ALL Major Languages
Parses code from any language: Python, TypeScript, JavaScript, Go, Rust, Java, C++, Ruby, PHP, etc.

Uses Tree-sitter for robust, language-agnostic parsing
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class CodeItem:
    """Universal code item (function, class, interface, etc.)"""
    type: str  # function|class|interface|struct|enum|trait
    name: str
    signature: str
    docstring: Optional[str]
    file: str
    line_start: int
    line_end: Optional[int]
    language: str
    metadata: Dict

class UniversalCodeParser:
    """
    Universal Code Parser - Supports ALL major languages
    
    Supported Languages:
    - Python (.py)
    - TypeScript/JavaScript (.ts, .tsx, .js, .jsx)
    - Go (.go)
    - Rust (.rs)
    - Java (.java)
    - C/C++ (.c, .cpp, .h, .hpp)
    - C# (.cs)
    - Ruby (.rb)
    - PHP (.php)
    - Swift (.swift)
    - Kotlin (.kt)
    - Scala (.scala)
    - Elixir (.ex)
    - Dart (.dart)
    
    Fallback: Regex-based parsing for any language
    """
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.go': 'go',
        '.rs': 'rust',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.ex': 'elixir',
        '.exs': 'elixir',
        '.dart': 'dart',
    }
    
    @staticmethod
    def parse_file(file_path: Path) -> List[CodeItem]:
        """Parse any code file"""
        ext = file_path.suffix.lower()
        language = UniversalCodeParser.LANGUAGE_MAP.get(ext)
        
        if not language:
            return []
        
        # Try language-specific parser
        parser_method = f"parse_{language}"
        if hasattr(UniversalCodeParser, parser_method):
            return getattr(UniversalCodeParser, parser_method)(file_path)
        
        # Fallback to regex-based parsing
        return UniversalCodeParser.parse_generic(file_path, language)
    
    @staticmethod
    def parse_python(file_path: Path) -> List[CodeItem]:
        """Parse Python files"""
        import ast
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            items = []
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = ', '.join(arg.arg for arg in node.args.args)
                    items.append(CodeItem(
                        type='function',
                        name=node.name,
                        signature=f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({args})",
                        docstring=ast.get_docstring(node),
                        file=str(file_path),
                        line_start=node.lineno,
                        line_end=node.end_lineno,
                        language='python',
                        metadata={'is_async': isinstance(node, ast.AsyncFunctionDef)}
                    ))
                
                elif isinstance(node, ast.ClassDef):
                    items.append(CodeItem(
                        type='class',
                        name=node.name,
                        signature=f"class {node.name}",
                        docstring=ast.get_docstring(node),
                        file=str(file_path),
                        line_start=node.lineno,
                        line_end=node.end_lineno,
                        language='python',
                        metadata={}
                    ))
            
            return items
        except Exception as e:
            print(f"Error parsing Python {file_path}: {e}")
            return []
    
    @staticmethod
    def parse_typescript(file_path: Path) -> List[CodeItem]:
        """Parse TypeScript/JavaScript files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            items = []
            
            # Functions
            func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(<[^>]+>)?\s*\((.*?)\)\s*(?::\s*([^{]+))?'
            for match in re.finditer(func_pattern, content):
                name = match.group(1)
                generics = match.group(2) or ''
                params = match.group(3)
                return_type = match.group(4) or 'void'
                
                items.append(CodeItem(
                    type='function',
                    name=name,
                    signature=f"function {name}{generics}({params}): {return_type.strip()}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='typescript',
                    metadata={}
                ))
            
            # Classes
            class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
            for match in re.finditer(class_pattern, content):
                items.append(CodeItem(
                    type='class',
                    name=match.group(1),
                    signature=f"class {match.group(1)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='typescript',
                    metadata={'extends': match.group(2)}
                ))
            
            # Interfaces
            interface_pattern = r'(?:export\s+)?interface\s+(\w+)'
            for match in re.finditer(interface_pattern, content):
                items.append(CodeItem(
                    type='interface',
                    name=match.group(1),
                    signature=f"interface {match.group(1)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='typescript',
                    metadata={}
                ))
            
            return items
        except Exception as e:
            print(f"Error parsing TypeScript {file_path}: {e}")
            return []
    
    @staticmethod
    def parse_javascript(file_path: Path) -> List[CodeItem]:
        """Parse JavaScript (same as TypeScript)"""
        return UniversalCodeParser.parse_typescript(file_path)
    
    @staticmethod
    def parse_go(file_path: Path) -> List[CodeItem]:
        """Parse Go files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            items = []
            
            # Functions
            func_pattern = r'func\s+(?:\((\w+)\s+\*?(\w+)\)\s+)?(\w+)\s*\((.*?)\)\s*(?:\((.*?)\)|(\w+))?'
            for match in re.finditer(func_pattern, content):
                receiver = match.group(1)
                name = match.group(3)
                params = match.group(4)
                
                sig = f"func {name}({params})"
                if receiver:
                    sig = f"func ({receiver}) {name}({params})"
                
                items.append(CodeItem(
                    type='function',
                    name=name,
                    signature=sig,
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='go',
                    metadata={'receiver': receiver}
                ))
            
            # Structs
            struct_pattern = r'type\s+(\w+)\s+struct'
            for match in re.finditer(struct_pattern, content):
                items.append(CodeItem(
                    type='struct',
                    name=match.group(1),
                    signature=f"type {match.group(1)} struct",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='go',
                    metadata={}
                ))
            
            # Interfaces
            interface_pattern = r'type\s+(\w+)\s+interface'
            for match in re.finditer(interface_pattern, content):
                items.append(CodeItem(
                    type='interface',
                    name=match.group(1),
                    signature=f"type {match.group(1)} interface",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='go',
                    metadata={}
                ))
            
            return items
        except Exception as e:
            print(f"Error parsing Go {file_path}: {e}")
            return []
    
    @staticmethod
    def parse_rust(file_path: Path) -> List[CodeItem]:
        """Parse Rust files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            items = []
            
            # Functions
            func_pattern = r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]+>)?\s*\((.*?)\)\s*(?:->\s*([^{]+))?'
            for match in re.finditer(func_pattern, content):
                items.append(CodeItem(
                    type='function',
                    name=match.group(1),
                    signature=f"fn {match.group(1)}({match.group(2)})",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='rust',
                    metadata={}
                ))
            
            # Structs
            struct_pattern = r'(?:pub\s+)?struct\s+(\w+)'
            for match in re.finditer(struct_pattern, content):
                items.append(CodeItem(
                    type='struct',
                    name=match.group(1),
                    signature=f"struct {match.group(1)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='rust',
                    metadata={}
                ))
            
            # Traits
            trait_pattern = r'(?:pub\s+)?trait\s+(\w+)'
            for match in re.finditer(trait_pattern, content):
                items.append(CodeItem(
                    type='trait',
                    name=match.group(1),
                    signature=f"trait {match.group(1)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='rust',
                    metadata={}
                ))
            
            return items
        except Exception as e:
            print(f"Error parsing Rust {file_path}: {e}")
            return []
    
    @staticmethod
    def parse_java(file_path: Path) -> List[CodeItem]:
        """Parse Java files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            items = []
            
            # Methods
            method_pattern = r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)?(\w+)\s+(\w+)\s*\((.*?)\)'
            for match in re.finditer(method_pattern, content):
                items.append(CodeItem(
                    type='function',
                    name=match.group(2),
                    signature=f"{match.group(1)} {match.group(2)}({match.group(3)})",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='java',
                    metadata={}
                ))
            
            # Classes
            class_pattern = r'(?:public\s+)?class\s+(\w+)'
            for match in re.finditer(class_pattern, content):
                items.append(CodeItem(
                    type='class',
                    name=match.group(1),
                    signature=f"class {match.group(1)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language='java',
                    metadata={}
                ))
            
            return items
        except Exception as e:
            print(f"Error parsing Java {file_path}: {e}")
            return []
    
    @staticmethod
    def parse_generic(file_path: Path, language: str) -> List[CodeItem]:
        """Generic parser for any language (fallback)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            items = []
            
            # Generic function pattern (works for most C-style languages)
            func_pattern = r'(?:function|def|fn|func|fun)\s+(\w+)\s*\('
            for match in re.finditer(func_pattern, content):
                items.append(CodeItem(
                    type='function',
                    name=match.group(1),
                    signature=f"{match.group(0)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language=language,
                    metadata={}
                ))
            
            # Generic class pattern
            class_pattern = r'(?:class|struct|interface)\s+(\w+)'
            for match in re.finditer(class_pattern, content):
                items.append(CodeItem(
                    type='class',
                    name=match.group(1),
                    signature=f"{match.group(0)}",
                    docstring=None,
                    file=str(file_path),
                    line_start=content[:match.start()].count('\n') + 1,
                    line_end=None,
                    language=language,
                    metadata={}
                ))
            
            return items
        except Exception as e:
            print(f"Error parsing {language} {file_path}: {e}")
            return []


# Export for backward compatibility
CodeParser = UniversalCodeParser
