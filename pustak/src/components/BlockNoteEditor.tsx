"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

// Dynamically import BlockNote to avoid SSR issues
const BlockNoteEditorComponent = dynamic(
  () => import("./BlockNoteEditorClient"),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center min-h-[400px] text-slate-400">
        Loading editor...
      </div>
    ),
  }
);

interface BlockNoteEditorProps {
  initialContent: string;
  onChange?: (markdown: string) => void;
  editable?: boolean;
  className?: string;
}

export function BlockNoteEditor(props: BlockNoteEditorProps) {
  return <BlockNoteEditorComponent {...props} />;
}

