import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { DetectionsPayload, ServerEvent, WorkspaceState } from "../api/types";

export type ConnectionState = "connecting" | "open" | "closed";

export interface Notice {
  id: number;
  title: string;
  message: string;
}

function createRefresher<T>(load: () => Promise<T>, apply: (value: T) => void, onError: (error: unknown) => void) {
  let isRunning = false;
  let isDirty = false;
  const run = async () => {
    if (isRunning) {
      isDirty = true;
      return;
    }
    isRunning = true;
    try {
      do {
        isDirty = false;
        apply(await load());
      } while (isDirty);
    } catch (error) {
      onError(error);
    } finally {
      isRunning = false;
    }
  };
  return run;
}

export function useWorkspace() {
  const [state, setState] = useState<WorkspaceState | null>(null);
  const [detections, setDetections] = useState<DetectionsPayload | null>(null);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [classSetsVersion, setClassSetsVersion] = useState(0);
  const [notices, setNotices] = useState<Notice[]>([]);
  const noticeCounter = useRef(0);

  const pushNotice = useCallback((title: string, message: string) => {
    noticeCounter.current += 1;
    const id = noticeCounter.current;
    setNotices((current) => [...current, { id, title, message }]);
  }, []);

  const dismissNotice = useCallback((id: number) => {
    setNotices((current) => current.filter((notice) => notice.id !== id));
  }, []);

  const refreshers = useRef<{ state: () => Promise<void>; detections: () => Promise<void> } | null>(null);
  if (refreshers.current === null) {
    const report = () => setConnection("closed");
    refreshers.current = {
      state: createRefresher(api.state, setState, report),
      detections: createRefresher(api.detections, setDetections, report),
    };
  }

  const refreshState = useCallback(() => void refreshers.current?.state(), []);
  const refreshDetections = useCallback(() => void refreshers.current?.detections(), []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let isDisposed = false;
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocol}//${window.location.host}/api/events`);
      setConnection("connecting");
      socket.onopen = () => {
        setConnection("open");
        refreshState();
        refreshDetections();
        setClassSetsVersion((version) => version + 1);
      };
      socket.onmessage = (message: MessageEvent<string>) => {
        const event = JSON.parse(message.data) as ServerEvent;
        switch (event.type) {
          case "changed":
            if (event.topics.includes("state")) refreshState();
            if (event.topics.includes("detections")) refreshDetections();
            if (event.topics.includes("class_sets")) setClassSetsVersion((version) => version + 1);
            break;
          case "notice":
            pushNotice(event.title, event.message);
            break;
        }
      };
      socket.onclose = () => {
        if (isDisposed) return;
        setConnection("closed");
        retryTimer = window.setTimeout(connect, 1500);
      };
    };
    connect();
    return () => {
      isDisposed = true;
      window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [refreshState, refreshDetections, pushNotice]);

  return {
    state,
    detections,
    connection,
    classSetsVersion,
    notices,
    pushNotice,
    dismissNotice,
    refreshState,
    refreshDetections,
  };
}
