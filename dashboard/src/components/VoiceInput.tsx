"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff } from "lucide-react";
import { cn, WS_URL } from "@/lib/utils";

interface VoiceInputProps {
  /** Called continuously with interim transcription (fill the input box) */
  onInterim?: (text: string) => void;
  /** Called with the final transcript when user stops */
  onFinal?: (text: string) => void;
  className?: string;
  size?: "sm" | "md";
}

/**
 * Voice input button that streams audio to Deepgram Nova-3 via backend WebSocket.
 * Fills the parent's input box with real-time transcription.
 * Does NOT auto-send — user decides when to submit.
 */
export function VoiceInput({ onInterim, onFinal, className, size = "md" }: VoiceInputProps) {
  const [listening, setListening] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const accumulatedRef = useRef("");

  const cleanup = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      try { recorderRef.current.stop(); } catch {}
      recorderRef.current = null;
    }
    if (wsRef.current) {
      try {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "stop" }));
        }
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setListening(false);
  }, []);

  const start = useCallback(async () => {
    // Clean up any previous session
    cleanup();
    accumulatedRef.current = "";

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const wsUrl = WS_URL.replace("/ws", "/ws/voice");
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus" : "audio/webm";
        const recorder = new MediaRecorder(stream, { mimeType });
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        };
        recorder.start(250);
        recorderRef.current = recorder;
        setListening(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "transcript") {
            if (data.is_final && data.text) {
              // Append final text to accumulated transcript
              accumulatedRef.current = (accumulatedRef.current + " " + data.text).trim();
              onInterim?.(accumulatedRef.current);
            } else if (data.text) {
              // Show interim: accumulated + current interim
              const preview = (accumulatedRef.current + " " + data.text).trim();
              onInterim?.(preview);
            }
          }
        } catch {}
      };

      ws.onerror = () => cleanup();
      ws.onclose = () => {
        // When WS closes, finalize the transcript
        if (accumulatedRef.current) {
          onFinal?.(accumulatedRef.current);
        }
        setListening(false);
      };

      wsRef.current = ws;
    } catch {
      cleanup();
    }
  }, [onInterim, onFinal, cleanup]);

  const stop = useCallback(() => {
    // Finalize transcript
    if (accumulatedRef.current) {
      onFinal?.(accumulatedRef.current);
    }
    cleanup();
  }, [onFinal, cleanup]);

  const toggle = useCallback(() => {
    if (listening) stop(); else start();
  }, [listening, start, stop]);

  useEffect(() => { return () => cleanup(); }, [cleanup]);

  const iconSize = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
  const btnSize = size === "sm" ? "h-8 w-8" : "h-10 w-10";

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <motion.button
        type="button"
        onClick={toggle}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className={cn(
          "relative flex items-center justify-center rounded-xl transition-all",
          btnSize,
          listening
            ? "bg-red-500 text-white shadow-lg shadow-red-500/30"
            : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-violet-400",
        )}
        title={listening ? "Stop recording" : "Voice input"}
      >
        {listening && (
          <motion.span
            className="absolute inset-0 rounded-xl border-2 border-red-400"
            initial={{ scale: 1, opacity: 1 }}
            animate={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
        )}
        {listening ? <MicOff className={iconSize} /> : <Mic className={iconSize} />}
      </motion.button>

      {/* Minimal waveform indicator when listening */}
      <AnimatePresence>
        {listening && (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            className="flex items-center gap-0.5 overflow-hidden"
          >
            {[0, 1, 2, 3, 4].map((i) => (
              <motion.div
                key={i}
                className="w-[2px] bg-red-400 rounded-full"
                animate={{ height: [3, 12 + Math.random() * 8, 3] }}
                transition={{ duration: 0.4 + Math.random() * 0.3, repeat: Infinity, delay: i * 0.08 }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
