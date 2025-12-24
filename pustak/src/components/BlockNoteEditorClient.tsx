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
  const lastContentRef = useRef<string>("");
  const isUpdatingRef = useRef(false);

  // Create the editor instance - start with empty, then load markdown
  const editor = useCreateBlockNote({});

  // Initialize editor with markdown content (and re-initialize when content changes)
  useEffect(() => {
    if (!editor) return;

    // Skip if content hasn't changed
    if (lastContentRef.current === initialContent && isInitialized) {
      return;
    }

    const initializeContent = async () => {
      try {
        isUpdatingRef.current = true;

        // Use the editor's built-in markdown parser
        const blocks = editor.tryParseMarkdownToBlocks(initialContent || "");
        if (blocks && blocks.length > 0) {
          // Replace the document with parsed blocks
          editor.replaceBlocks(editor.document, blocks);
        } else {
          // Empty content - clear the editor
          editor.replaceBlocks(editor.document, []);
        }

        lastContentRef.current = initialContent || "";
        setIsInitialized(true);
        isUpdatingRef.current = false;
      } catch (error) {
        console.error("Error initializing editor with markdown:", error);
        setIsInitialized(true);
        isUpdatingRef.current = false;
      }
    };

    initializeContent();
  }, [editor, initialContent]);

  // Handle content changes
  useEffect(() => {
    if (!onChangeRef.current || !editable || !editor || !isInitialized) return;

    const handleChange = () => {
      // Don't trigger onChange during initialization/updates
      if (isUpdatingRef.current) return;

      try {
        // Convert blocks back to markdown
        const markdown = editor.blocksToMarkdownLossy(editor.document);

        // Only call onChange if content actually changed
        if (markdown !== lastContentRef.current) {
          onChangeRef.current?.(markdown);
        }
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
      <BlockNoteView editor={editor} theme="dark" editable={editable} />
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
