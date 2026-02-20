import { useState, useEffect, useCallback, useRef } from "react";

const MIN_WIDTH = 320;
const MAX_WIDTH_RATIO = 0.9; // 90% of viewport

/**
 * Hook for making a right-side panel resizable by dragging its left edge.
 *
 * @param {string} storageKey - localStorage key to persist the width
 * @param {number} defaultWidth - default panel width in pixels
 * @returns {{ width, isDragging, handleMouseDown }}
 */
export default function useResizablePanel(storageKey, defaultWidth) {
  const [width, setWidth] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = Number(saved);
        if (parsed >= MIN_WIDTH) return parsed;
      }
    } catch {}
    return defaultWidth;
  });

  const isDraggingRef = useRef(false);
  const [isDragging, setIsDragging] = useState(false);

  // Clamp width to valid range on window resize
  useEffect(() => {
    function handleResize() {
      const maxWidth = window.innerWidth * MAX_WIDTH_RATIO;
      setWidth((prev) => Math.min(prev, maxWidth));
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Persist width to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, String(Math.round(width)));
    } catch {}
  }, [storageKey, width]);

  const handleMouseDown = useCallback(
    (e) => {
      e.preventDefault();
      isDraggingRef.current = true;
      setIsDragging(true);

      const startX = e.clientX;
      const startWidth = width;

      function onMouseMove(e) {
        if (!isDraggingRef.current) return;
        // Panel is on the right, so dragging left (smaller clientX) = wider panel
        const delta = startX - e.clientX;
        const maxWidth = window.innerWidth * MAX_WIDTH_RATIO;
        const newWidth = Math.max(MIN_WIDTH, Math.min(startWidth + delta, maxWidth));
        setWidth(newWidth);
      }

      function onMouseUp() {
        isDraggingRef.current = false;
        setIsDragging(false);
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      }

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [width],
  );

  return { width, isDragging, handleMouseDown };
}
