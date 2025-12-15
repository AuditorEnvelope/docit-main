"use client";

import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import "@blocknote/core/fonts/inter.css";
import "@blocknote/mantine/style.css";
import { useEffect, useRef, useState } from "react";

interface BlockNoteEditorClientProps {
  initialContent: string;
  onChange?: (markdown: string) => void;
  editable?: boolean;
  className?: string;
}

export default function BlockNoteEditorClient({
  initialContent,
  onChange,
  editable = true,
  className = "",
}: BlockNoteEditorClientProps) {
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const [isInitialized, setIsInitialized] = useState(false);

  // Create the editor instance - start with empty, then load markdown
  const editor = useCreateBlockNote({
    editable,
  });

  // Initialize editor with markdown content
  useEffect(() => {
    if (!editor || isInitialized || !initialContent) return;

    const initializeContent = async () => {
      try {
        // Use the editor's built-in markdown parser
        const blocks = editor.tryParseMarkdownToBlocks(initialContent);
        if (blocks && blocks.length > 0) {
          // Replace the document with parsed blocks
          editor.replaceBlocks(editor.document, blocks);
        }
        setIsInitialized(true);
      } catch (error) {
        console.error("Error initializing editor with markdown:", error);
        setIsInitialized(true);
      }
    };

    initializeContent();
  }, [editor, initialContent, isInitialized]);

  // Handle content changes
  useEffect(() => {
    if (!onChangeRef.current || !editable || !editor || !isInitialized) return;

    const handleChange = () => {
      try {
        // Convert blocks back to markdown
        const markdown = editor.blocksToMarkdownLossy(editor.document);
        onChangeRef.current?.(markdown);
      } catch (error) {
        console.error("Error converting blocks to markdown:", error);
      }
    };

    // Subscribe to editor changes
    editor.onChange(handleChange);

    return () => {
      // Cleanup if needed
    };
  }, [editor, editable, isInitialized]);

  return (
    <div className={`blocknote-editor ${className}`}>
      <BlockNoteView editor={editor} theme="dark" />
      <style jsx global>{`
        .blocknote-editor {
          min-height: 400px;
        }
        .blocknote-editor .bn-container {
          background: transparent;
        }
        .blocknote-editor .bn-editor {
          color: rgb(226, 232, 240);
        }
      `}</style>
    </div>
  );
}

