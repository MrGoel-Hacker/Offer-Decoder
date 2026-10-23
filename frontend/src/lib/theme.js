import { useSyncExternalStore } from "react";

const KEY = "od-theme";
const listeners = new Set();

export const getTheme = () => {
  try {
    return localStorage.getItem(KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
};

export const applyTheme = (t) => {
  document.documentElement.classList.toggle("light", t === "light");
  document.documentElement.classList.toggle("dark", t !== "light");
};

export const setTheme = (t) => {
  try {
    localStorage.setItem(KEY, t);
  } catch {}
  applyTheme(t);
  listeners.forEach((l) => l());
};

const subscribe = (l) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

export const useTheme = () => useSyncExternalStore(subscribe, getTheme);
