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
  const lastExternalContentRef = useRef<string>("");
  const isUserTypingRef = useRef(false);

  // Create the editor instance ONCE - never recreate
  const editor = useCreateBlockNote({});

  // Initialize editor ONLY on mount or external content change (not user typing)
  useEffect(() => {
    if (!editor) return;

    // CRITICAL: Skip if user is typing (not an external change)
    if (isUserTypingRef.current) {
      return;
    }

    // Skip if content hasn't actually changed from external source
    if (lastExternalContentRef.current === initialContent && isInitialized) {
      return;
    }

    const initializeContent = async () => {
      try {
        // Use the editor's built-in markdown parser
        const blocks = editor.tryParseMarkdownToBlocks(initialContent || "");
        if (blocks && blocks.length > 0) {
          // Replace the document with parsed blocks
          editor.replaceBlocks(editor.document, blocks);
        } else {
          // Empty content - clear the editor
          editor.replaceBlocks(editor.document, []);
        }

        lastExternalContentRef.current = initialContent || "";
        setIsInitialized(true);
      } catch (error) {
        console.error("Error initializing editor with markdown:", error);
        setIsInitialized(true);
      }
    };

    initializeContent();
  }, [editor, initialContent, isInitialized]);

  // Handle content changes from USER TYPING
  useEffect(() => {
    if (!onChangeRef.current || !editable || !editor || !isInitialized) return;

    const handleChange = () => {
      // Mark that user is typing (prevents re-initialization)
      isUserTypingRef.current = true;

      try {
        // Convert blocks back to markdown
        const markdown = editor.blocksToMarkdownLossy(editor.document);

        // Only call onChange if content actually changed
        if (markdown !== lastExternalContentRef.current) {
          onChangeRef.current?.(markdown);
        }
      } catch (error) {
        console.error("Error converting blocks to markdown:", error);
      }

      // Reset typing flag after short delay
      setTimeout(() => {
        isUserTypingRef.current = false;
      }, 100);
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
