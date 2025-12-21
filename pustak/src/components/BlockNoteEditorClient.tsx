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
  const [isLoading, setIsLoading] = useState(true);
  const previousContentRef = useRef<string>("");
  const isUpdatingRef = useRef(false);

  // Create the editor instance
  const editor = useCreateBlockNote({});

  // Initialize/update editor with markdown content
  useEffect(() => {
    if (!editor) return;

    // Skip if content hasn't changed
    if (previousContentRef.current === initialContent) {
      setIsLoading(false);
      return;
    }

    // Mark that we're updating to prevent onChange from firing during initialization
    isUpdatingRef.current = true;

    const initializeContent = async () => {
      try {
        console.log(
          "📝 Initializing BlockNote editor with content length:",
          initialContent.length
        );

        // Parse markdown to blocks
        const blocks = editor.tryParseMarkdownToBlocks(initialContent || "");

        if (blocks && blocks.length > 0) {
          // Replace the entire document with new blocks
          editor.replaceBlocks(editor.document, blocks);
          console.log(
            "✅ BlockNote editor initialized with",
            blocks.length,
            "blocks"
          );
        } else {
          // Even if empty, initialize with a default paragraph
          editor.replaceBlocks(editor.document, [
            {
              type: "paragraph",
              content: "",
            },
          ]);
          console.log("✅ BlockNote editor initialized with empty content");
        }

        previousContentRef.current = initialContent;
        setIsLoading(false);
      } catch (error) {
        console.error("❌ Error initializing editor with markdown:", error);
        setIsLoading(false);
      } finally {
        isUpdatingRef.current = false;
      }
    };

    initializeContent();
  }, [editor, initialContent]);

  // Handle content changes (only after initial load)
  useEffect(() => {
    if (!onChangeRef.current || !editable || !editor || isLoading) return;

    const handleChange = () => {
      // Don't fire onChange during initialization/updates
      if (isUpdatingRef.current) return;

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
      // Cleanup handled by BlockNote
    };
  }, [editor, editable, isLoading]);

  if (isLoading) {
    return (
      <div
        className={`flex items-center justify-center min-h-[400px] text-slate-400 ${className}`}
      >
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-500 mx-auto mb-2"></div>
          <p className="text-sm">Loading editor...</p>
        </div>
      </div>
    );
  }

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
        .blocknote-editor .bn-editor p {
          color: rgb(226, 232, 240);
        }
      `}</style>
    </div>
  );
}
