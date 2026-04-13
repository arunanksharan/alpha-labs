import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8100/ws";
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** Prefix a path with BASE_PATH for navigation */
export function href(path: string): string {
  return `${BASE_PATH}${path}`;
}
