/**
 * shared/hooks/useNotification.ts
 *
 * In-component notification / message-bar state management hook.
 *
 * Manages a list of ephemeral notification messages that workload UIs display
 * in their message bar area. Supports multiple concurrent notifications,
 * individual or bulk dismissal, and optional auto-close timers.
 *
 * Usage:
 *   const { notifications, show, dismiss, dismissAll } = useNotification();
 *
 *   // Show a success message
 *   show({ type: "success", title: "Saved", message: "Item saved successfully." });
 *
 *   // Show an error with auto-close after 5 seconds
 *   show({ type: "error", message: "Connection failed.", autoCloseMs: 5000 });
 *
 *   // Dismiss a specific notification by ID
 *   dismiss(id);
 *
 *   // Dismiss all active notifications
 *   dismissAll();
 *
 *   // Render with Fluent UI MessageBar
 *   {notifications.map(n => (
 *     <MessageBar key={n.id} intent={n.type} onDismiss={() => dismiss(n.id)}>
 *       <MessageBarBody>{n.message}</MessageBarBody>
 *     </MessageBar>
 *   ))}
 */
import { useState, useCallback, useEffect, useRef } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export type NotificationType = "success" | "error" | "warning" | "info";

export interface NotificationMessage {
  /** Unique identifier assigned by `show()`. Use this to dismiss. */
  id: string;
  /** Visual intent / severity of the message. */
  type: NotificationType;
  /** Short human-readable description of the event. */
  message: string;
  /** Optional bold title shown above the message body. */
  title?: string;
  /**
   * Auto-dismiss after this many milliseconds.
   * Omit (or set to 0) to require manual dismissal.
   */
  autoCloseMs?: number;
}

export interface UseNotificationReturn {
  /** All currently active notifications, in chronological order (oldest first). */
  notifications: NotificationMessage[];
  /**
   * Add a new notification.
   * @returns The generated `id` — store it if you need to dismiss programmatically.
   */
  show: (notification: Omit<NotificationMessage, "id">) => string;
  /** Remove a single notification by its `id`. No-op if already dismissed. */
  dismiss: (id: string) => void;
  /** Remove all active notifications at once. */
  dismissAll: () => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * Manages notification messages for a workload item editor.
 *
 * @example
 * ```tsx
 * function MyEditor() {
 *   const { notifications, show, dismiss } = useNotification();
 *
 *   async function handleSave() {
 *     try {
 *       await save();
 *       show({ type: "success", message: "Saved successfully.", autoCloseMs: 3000 });
 *     } catch {
 *       show({ type: "error", title: "Save failed", message: "Please try again." });
 *     }
 *   }
 *   ...
 * }
 * ```
 */
export function useNotification(): UseNotificationReturn {
  const [notifications, setNotifications] = useState<NotificationMessage[]>([]);

  // Track pending auto-close timers so we can clear them on unmount.
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

  // Clear all timers on unmount to prevent state updates after unmount.
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
      timers.clear();
    };
  }, []);

  const dismiss = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    const timer = timersRef.current.get(id);
    if (timer !== undefined) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const show = useCallback(
    (notification: Omit<NotificationMessage, "id">): string => {
      const id = `notif_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const entry: NotificationMessage = { ...notification, id };
      setNotifications((prev) => [...prev, entry]);

      if (notification.autoCloseMs && notification.autoCloseMs > 0) {
        const timer = setTimeout(() => dismiss(id), notification.autoCloseMs);
        timersRef.current.set(id, timer);
      }

      return id;
    },
    [dismiss],
  );

  const dismissAll = useCallback(() => {
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current.clear();
    setNotifications([]);
  }, []);

  return { notifications, show, dismiss, dismissAll };
}
