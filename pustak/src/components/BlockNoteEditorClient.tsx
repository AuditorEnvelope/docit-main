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
        /* TODO: Replace hardcoded color values below with Tailwind-driven CSS variables
           or a shared theme token system so BlockNote styling stays in sync with Tailwind. */
        /* BlockNote CSS Variables - Match DocIt Theme */
        .blocknote-editor {
          --bn-colors-menu-background: rgb(
            15,
            23,
            42
          ) !important; /* slate-900 */
          --bn-colors-menu-text: rgb(226, 232, 240) !important; /* slate-200 */
          --bn-colors-menu-hovered-background: rgb(
            51,
            65,
            85
          ) !important; /* slate-700 */
          --bn-colors-menu-hovered-text: rgb(226, 232, 240) !important;
          --bn-colors-menu-selected-background: rgb(51, 65, 85) !important;
          --bn-colors-menu-selected-text: rgb(226, 232, 240) !important;
          --bn-colors-menu-border: rgb(51, 65, 85) !important; /* slate-700 */
          --bn-colors-menu-shadow: rgba(0, 0, 0, 0.5) !important;
        }
        /* Main container */
        .blocknote-editor {
          min-height: 400px;
          font-size: 15px;
        }

        /* Remove ugly gray background */
        .blocknote-editor .bn-container,
        .blocknote-editor .bn-editor,
        .blocknote-editor .ProseMirror {
          background: transparent !important;
          background-color: transparent !important;
        }

        /* Text color and sizing */
        .blocknote-editor .bn-editor,
        .blocknote-editor .ProseMirror {
          color: rgb(226, 232, 240) !important;
          font-size: 15px !important;
          line-height: 1.6 !important;
        }

        /* Paragraphs */
        .blocknote-editor p {
          font-size: 15px !important;
          line-height: 1.6 !important;
          margin: 0.5rem 0 !important;
        }

        /* Block backgrounds */
        .blocknote-editor .bn-block-outer,
        .blocknote-editor [class*="bn-block"] {
          background: transparent !important;
        }

        /* Headings - More compact */
        .blocknote-editor h1 {
          color: rgb(255, 255, 255) !important;
          font-size: 2rem !important;
          line-height: 1.2 !important;
          margin: 1.5rem 0 0.75rem 0 !important;
          font-weight: 700 !important;
        }

        .blocknote-editor h2 {
          color: rgb(255, 255, 255) !important;
          font-size: 1.5rem !important;
          line-height: 1.3 !important;
          margin: 1.25rem 0 0.625rem 0 !important;
          font-weight: 600 !important;
        }

        .blocknote-editor h3 {
          color: rgb(255, 255, 255) !important;
          font-size: 1.25rem !important;
          line-height: 1.4 !important;
          margin: 1rem 0 0.5rem 0 !important;
          font-weight: 600 !important;
        }

        .blocknote-editor h4 {
          color: rgb(255, 255, 255) !important;
          font-size: 1.1rem !important;
          line-height: 1.4 !important;
          margin: 0.875rem 0 0.5rem 0 !important;
          font-weight: 600 !important;
        }

        .blocknote-editor h5,
        .blocknote-editor h6 {
          color: rgb(255, 255, 255) !important;
          font-size: 1rem !important;
          line-height: 1.4 !important;
          margin: 0.75rem 0 0.5rem 0 !important;
          font-weight: 600 !important;
        }

        /* Code blocks */
        .blocknote-editor pre {
          background: rgb(30, 41, 59) !important;
          color: rgb(226, 232, 240) !important;
          font-size: 13px !important;
          padding: 0.75rem !important;
          border-radius: 0.375rem !important;
          margin: 0.75rem 0 !important;
        }

        .blocknote-editor pre code {
          font-size: 13px !important;
        }

        /* Inline code */
        .blocknote-editor p code,
        .blocknote-editor li code {
          background: rgb(51, 65, 85) !important;
          color: rgb(226, 232, 240) !important;
          padding: 0.125rem 0.375rem !important;
          border-radius: 0.25rem !important;
          font-size: 13px !important;
        }

        /* Links */
        .blocknote-editor a {
          color: rgb(96, 165, 250) !important;
          font-size: 15px !important;
        }

        /* Blockquotes */
        .blocknote-editor blockquote {
          border-left: 3px solid rgb(59, 130, 246);
          background: rgb(30, 41, 59) !important;
          padding: 0.75rem 1rem !important;
          margin: 0.75rem 0 !important;
          font-size: 15px !important;
        }

        /* Lists - More compact */
        .blocknote-editor ul,
        .blocknote-editor ol {
          color: rgb(226, 232, 240) !important;
          margin: 0.5rem 0 !important;
          padding-left: 1.5rem !important;
        }

        .blocknote-editor li {
          font-size: 15px !important;
          line-height: 1.6 !important;
          margin: 0.25rem 0 !important;
        }

        /* Strong/Bold */
        .blocknote-editor strong,
        .blocknote-editor b {
          font-weight: 600 !important;
        }

        /* Selection */
        .blocknote-editor ::selection {
          background: rgb(59, 130, 246, 0.3) !important;
        }

        /* Side menu */
        .blocknote-editor [class*="sideMenu"],
        .blocknote-editor [class*="bn-side-menu"] {
          background: rgb(30, 41, 59) !important;
        }

        /* Formatting toolbar */
        .blocknote-editor [class*="formattingToolbar"],
        .blocknote-editor [class*="bn-formatting-toolbar"] {
          background: rgb(30, 41, 59) !important;
          border: 1px solid rgb(51, 65, 85) !important;
        }

        /* ===== SLASH COMMAND MENU ===== */
        /* Styles are in globals.css because menu renders in portal */
      `}</style>
    </div>
  );
}
