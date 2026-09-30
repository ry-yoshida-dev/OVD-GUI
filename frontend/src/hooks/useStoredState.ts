import { useEffect, useState } from "react";

export function useStoredState<T extends object>(key: string, initial: T): [T, (value: T | ((current: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = window.localStorage.getItem(key);
      return stored === null ? initial : { ...initial, ...(JSON.parse(stored) as T) };
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage may be unavailable */
    }
  }, [key, value]);
  return [value, setValue];
}
