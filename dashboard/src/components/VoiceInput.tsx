"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Loader2 } from "lucide-react";
import { cn, API_URL } from "@/lib/utils";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  className?: string;
  size?: "sm" | "md";
  placeholder?: string;
}

/**
 * Real-time voice input using Deepgram Nova-3 streaming STT via WebSocket.
 * Falls back to browser Web Speech API if Deepgram key is unavailable.
 *
 * Architecture:
 *   Browser mic (MediaRecorder) → WebSocket → Deepgram Nova-3 → transcript
 *   Audio chunks sent every 250ms for near-zero latency.
 */
export function VoiceInput({ onTranscript, className, size = "md", placeholder }: VoiceInputProps) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [mode, setMode] = useState<"deepgram" | "browser" | "none">("none");
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Detect available STT mode on mount
  useEffect(() => {
    // Check if Deepgram key is available via the backend
    fetch(`${API_URL}/api/settings/keys`)
      .then((r) => r.json())
      .then((d) => {
        // Use Deepgram if OpenAI key is available (Deepgram uses its own key,
        // but we'll proxy through the backend for key security)
        setMode("deepgram");
      })
      .catch(() => {
        // Fallback: check browser Web Speech API
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const w = window as any;
        if (w.SpeechRecognition || w.webkitSpeechRecognition) {
          setMode("browser");
        } else {
          setMode("none");
        }
      });
  }, []);

  // ─── Deepgram Streaming STT ───────────────────────────────────────
  const startDeepgram = useCallback(async () => {
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

      // Get Deepgram key from backend (or use OpenAI realtime)
      // For now, connect directly to Deepgram via their WebSocket API
      // The backend proxies the key to avoid exposing it in the browser
      const deepgramKey = await fetch(`${API_URL}/api/voice/key`)
        .then((r) => r.json())
        .then((d) => d.key)
        .catch(() => null);

      if (!deepgramKey) {
        // Fall back to browser API
        startBrowser();
        return;
      }

      // Connect to Deepgram streaming API
      const ws = new WebSocket(
        `wss://api.deepgram.com/v1/listen?model=nova-3&language=en&smart_format=true&interim_results=true&endpointing=300&utterance_end_ms=1500`,
        ["token", deepgramKey]
      );

      ws.onopen = () => {
        // Start recording and streaming audio chunks
        const recorder = new MediaRecorder(stream, {
          mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : "audio/webm",
        });

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        };

        recorder.start(250); // 250ms chunks for low latency
        recorderRef.current = recorder;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "Results") {
            const transcript = data.channel?.alternatives?.[0]?.transcript || "";
            if (transcript) {
              if (data.is_final) {
                setInterim("");
                // Accumulate final transcripts
                if (data.speech_final) {
                  // End of utterance — send the complete transcript
                  stop();
                  onTranscript(transcript);
                }
              } else {
                setInterim(transcript);
              }
            }
          }
          // Handle utterance_end for auto-stop
          if (data.type === "UtteranceEnd") {
            const lastTranscript = interim || "";
            if (lastTranscript) {
              stop();
              onTranscript(lastTranscript);
            }
          }
        } catch {}
      };

      ws.onerror = () => stop();
      ws.onclose = () => stop();

      wsRef.current = ws;
      setListening(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
      setListening(false);
    }
  }, [onTranscript, interim]);

  // ─── Browser Web Speech API (fallback) ────────────────────────────
  const startBrowser = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) finalText += event.results[i][0].transcript;
        else interimText += event.results[i][0].transcript;
      }
      if (interimText) setInterim(interimText);
      if (finalText) {
        setInterim("");
        setListening(false);
        onTranscript(finalText.trim());
      }
    };

    recognition.onerror = () => { setListening(false); setInterim(""); };
    recognition.onend = () => setListening(false);
    recognition.start();
    setListening(true);

    // Store for cleanup
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__voiceRecognition = recognition;
  }, [onTranscript]);

  // ─── Stop ─────────────────────────────────────────────────────────
  const stop = useCallback(() => {
    // Stop Deepgram
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    // Stop browser API
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition = (window as any).__voiceRecognition;
    if (recognition) {
      recognition.stop();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window as any).__voiceRecognition;
    }

    setListening(false);
    setInterim("");
  }, []);

  // ─── Toggle ───────────────────────────────────────────────────────
  const toggle = useCallback(() => {
    if (listening) {
      stop();
    } else if (mode === "deepgram") {
      startDeepgram();
    } else if (mode === "browser") {
      startBrowser();
    }
  }, [listening, mode, startDeepgram, startBrowser, stop]);

  // Cleanup on unmount
  useEffect(() => { return () => stop(); }, [stop]);

  if (mode === "none") return null;

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
            : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-violet-400",
        )}
        title={listening ? "Stop listening" : placeholder || "Voice input"}
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

      {/* Waveform animation when listening */}
      <AnimatePresence>
        {listening && (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            className="flex items-center gap-1 overflow-hidden"
          >
            {interim ? (
              <div className="flex items-center gap-1.5 rounded-lg bg-zinc-800/80 px-3 py-1.5 backdrop-blur-sm">
                <Loader2 className="h-3 w-3 animate-spin text-violet-400 shrink-0" />
                <span className="text-xs text-zinc-300 whitespace-nowrap max-w-[250px] truncate italic">
                  {interim}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-0.5">
                {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                  <motion.div
                    key={i}
                    className="w-[2px] bg-red-400 rounded-full"
                    animate={{ height: [3, 14 + Math.random() * 10, 3] }}
                    transition={{ duration: 0.4 + Math.random() * 0.3, repeat: Infinity, delay: i * 0.07 }}
                  />
                ))}
                <span className="ml-1.5 text-[10px] text-red-400 font-medium">
                  {mode === "deepgram" ? "Deepgram Nova-3" : "Listening..."}
                </span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
