"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Loader2, Zap } from "lucide-react";
import { cn, WS_URL } from "@/lib/utils";

interface VoiceInputProps {
  /** Called with the final transcript when user finishes speaking */
  onTranscript: (text: string) => void;
  /** Called with streaming LLM response chunks (for real-time display) */
  onResponseChunk?: (chunk: string) => void;
  /** Called when the full response is complete */
  onResponseComplete?: (text: string) => void;
  /** Called on tool calls (for UI feedback) */
  onToolCall?: (tool: string, args: Record<string, unknown>) => void;
  className?: string;
  size?: "sm" | "md";
  placeholder?: string;
  /** If true, sends audio to the voice pipeline for LLM processing.
   *  If false, just transcribes and calls onTranscript. */
  pipelineMode?: boolean;
}

/**
 * Production voice input using Deepgram Nova-3 streaming STT via the
 * backend voice pipeline WebSocket.
 *
 * Architecture:
 *   Browser mic (MediaRecorder WebM/Opus)
 *     → WebSocket /ws/voice
 *       → Backend: Deepgram STT (streaming)
 *       → Backend: LLM with tool calling (research, backtest, signals)
 *     ← JSON messages (transcript, tool calls, response chunks)
 */
export function VoiceInput({
  onTranscript,
  onResponseChunk,
  onResponseComplete,
  onToolCall,
  className,
  size = "md",
  placeholder,
  pipelineMode = false,
}: VoiceInputProps) {
  const [listening, setListening] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [interim, setInterim] = useState("");
  const [status, setStatus] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // ─── Start voice session ──────────────────────────────────────
  const start = useCallback(async () => {
    try {
      // Get mic access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      // Connect to voice pipeline WebSocket
      const wsUrl = WS_URL.replace("/ws", "/ws/voice");
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setStatus("Connected to Deepgram Nova-3");

        // Start recording audio and streaming to server
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm";

        const recorder = new MediaRecorder(stream, { mimeType });

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        };

        recorder.start(250); // 250ms chunks for low latency
        recorderRef.current = recorder;
        setListening(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case "ready":
              setStatus(data.message || "Ready");
              break;

            case "transcript":
              if (data.is_final) {
                setInterim("");
                if (!pipelineMode) {
                  // Simple mode: just return the transcript
                  stop();
                  onTranscript(data.text);
                } else {
                  onTranscript(data.text);
                  setStatus("Processing...");
                  setProcessing(true);
                }
              } else {
                setInterim(data.text);
              }
              break;

            case "processing":
              setStatus(data.message || "Analyzing...");
              setProcessing(true);
              break;

            case "tool_call":
              setStatus(`Running ${data.tool}...`);
              onToolCall?.(data.tool, data.args || {});
              break;

            case "tool_result":
              setStatus("Synthesizing response...");
              break;

            case "response_chunk":
              onResponseChunk?.(data.text);
              break;

            case "response_complete":
              setProcessing(false);
              setStatus("");
              onResponseComplete?.(data.text);
              break;

            case "error":
              setStatus(`Error: ${data.message}`);
              setProcessing(false);
              setTimeout(() => setStatus(""), 3000);
              break;
          }
        } catch {}
      };

      ws.onerror = () => {
        setStatus("Connection error");
        stop();
      };

      ws.onclose = () => {
        if (listening) stop();
      };

      wsRef.current = ws;
    } catch (err) {
      setStatus("Microphone access denied");
      setTimeout(() => setStatus(""), 3000);
    }
  }, [onTranscript, onResponseChunk, onResponseComplete, onToolCall, pipelineMode, listening]);

  // ─── Stop ─────────────────────────────────────────────────────
  const stop = useCallback(() => {
    // Stop recorder
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
      recorderRef.current = null;
    }

    // Tell server we're done
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: "stop" }));
      } catch {}
      // Give server time to process, then close
      setTimeout(() => {
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      }, 5000);
    }

    // Stop mic
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    setListening(false);
    setInterim("");
  }, []);

  // ─── Toggle ───────────────────────────────────────────────────
  const toggle = useCallback(() => {
    if (listening) {
      stop();
    } else {
      start();
    }
  }, [listening, start, stop]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stop();
  }, [stop]);

  const iconSize = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
  const btnSize = size === "sm" ? "h-8 w-8" : "h-10 w-10";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Mic button */}
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
            : processing
              ? "bg-violet-500 text-white shadow-lg shadow-violet-500/30"
              : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-violet-400",
        )}
        title={listening ? "Stop" : placeholder || "Voice input (Deepgram Nova-3)"}
        disabled={processing}
      >
        {/* Pulse ring */}
        {(listening || processing) && (
          <motion.span
            className={cn(
              "absolute inset-0 rounded-xl border-2",
              listening ? "border-red-400" : "border-violet-400",
            )}
            initial={{ scale: 1, opacity: 1 }}
            animate={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
        )}
        {processing ? (
          <Loader2 className={cn(iconSize, "animate-spin")} />
        ) : listening ? (
          <MicOff className={iconSize} />
        ) : (
          <Mic className={iconSize} />
        )}
      </motion.button>

      {/* Status + waveform */}
      <AnimatePresence>
        {(listening || processing || status) && (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            className="flex items-center gap-1.5 overflow-hidden"
          >
            {interim ? (
              // Live transcription
              <div className="flex items-center gap-1.5 rounded-lg bg-zinc-800/80 px-3 py-1.5 backdrop-blur-sm">
                <Zap className="h-3 w-3 text-violet-400 shrink-0" />
                <span className="text-xs text-zinc-200 whitespace-nowrap max-w-[300px] truncate">
                  {interim}
                </span>
              </div>
            ) : listening ? (
              // Waveform animation
              <div className="flex items-center gap-0.5">
                {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                  <motion.div
                    key={i}
                    className="w-[2px] bg-red-400 rounded-full"
                    animate={{ height: [3, 14 + Math.random() * 10, 3] }}
                    transition={{ duration: 0.4 + Math.random() * 0.3, repeat: Infinity, delay: i * 0.07 }}
                  />
                ))}
                <span className="ml-1.5 text-[10px] text-red-400 font-medium">Deepgram Nova-3</span>
              </div>
            ) : status ? (
              // Status text
              <span className="text-[10px] text-zinc-500 whitespace-nowrap">{status}</span>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
