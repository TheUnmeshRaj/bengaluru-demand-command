"use client";

import { useEffect, useRef, useState } from "react";

interface VoiceHeliAssistantProps {
  onApplyVoiceRoute: (pickup: string, drop: string) => void;
}

export default function VoiceHeliAssistant({
  onApplyVoiceRoute,
}: VoiceHeliAssistantProps) {
  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>(
    "Tap the microphone or choose a voice prompt below"
  );
  const [selectedLanguage, setSelectedLanguage] = useState<"kannada" | "english">("kannada");
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animRef = useRef<number | null>(null);

  const samplePrompts = {
    kannada: [
      { text: "“ಇಂದಿರಾನಗರದಿಂದ ಏರ್‌ಪೋರ್ಟ್‌ಗೆ ಕ್ಯಾಬ್ ಹೇಳಿ”", pickup: "Indiranagar", drop: "KIAL Airport" },
      { text: "“ಕೋರಮಂಗಲದಿಂದ ಎಂ ಜಿ ರೋಡ್‌ಗೆ ಎಲೆಕ್ಟ್ರಿಕ್ ಕ್ಯಾಬ್”", pickup: "Koramangala", drop: "MG Road / CBD" },
      { text: "“ವೈಟ್‌ಫೀಲ್ಡ್‌ನಿಂದ ಹೆಚ್‌ಎಸ್ಆರ್‌ಗೆ ಪ್ರೈಮ್ ಸೆಡಾನ್”", pickup: "Whitefield", drop: "HSR Layout" },
    ],
    english: [
      { text: "“Heli: Book cab from Indiranagar to Airport”", pickup: "Indiranagar", drop: "KIAL Airport" },
      { text: "“Heli: Electric taxi from Koramangala to MG Road”", pickup: "Koramangala", drop: "MG Road / CBD" },
      { text: "“Heli: Prime sedan from Whitefield to HSR Layout”", pickup: "Whitefield", drop: "HSR Layout" },
    ],
  };

  // Simple clean voice wave canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = canvas.parentElement?.clientWidth || 280);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 44);

    let phase = 0;
    const render = () => {
      ctx.fillStyle = "#171920";
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = isListening ? "#d4ff00" : "#434d61";
      ctx.lineWidth = 1.5;

      ctx.beginPath();
      phase += 0.08;
      const amp = isListening ? 14 : 3;

      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin(x * 0.05 + phase) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      animRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isListening]);

  const handleSimulateVoice = (promptText: string, pickup: string, drop: string) => {
    setIsListening(true);
    setTranscript(`Listening: ${promptText}…`);

    setTimeout(() => {
      setIsListening(false);
      setTranscript(`Recognized: ${promptText} → Route set from ${pickup} to ${drop}`);
      onApplyVoiceRoute(pickup, drop);
    }, 1200);
  };

  return (
    <div className="bento-body">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Cultural Explanation Tag */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-hairline)",
            padding: "12px 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--lime)", fontWeight: 700 }}>
              LINGUISTIC FOUNDATION
            </div>
            <div style={{ fontSize: 12, color: "#fff", marginTop: 2 }}>
              In Kannada, <strong>“ಹೇಳಿ” (Heli)</strong> means <em>“Speak / Tell me”</em>
            </div>
          </div>

          <div style={{ display: "flex", gap: 4 }}>
            <button
              onClick={() => setSelectedLanguage("kannada")}
              style={{
                background: selectedLanguage === "kannada" ? "var(--lime)" : "transparent",
                color: selectedLanguage === "kannada" ? "#000" : "var(--text-secondary)",
                border: "1px solid var(--border-hairline)",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 700,
                padding: "4px 8px",
                cursor: "pointer",
              }}
            >
              ಕನ್ನಡ
            </button>
            <button
              onClick={() => setSelectedLanguage("english")}
              style={{
                background: selectedLanguage === "english" ? "var(--lime)" : "transparent",
                color: selectedLanguage === "english" ? "#000" : "var(--text-secondary)",
                border: "1px solid var(--border-hairline)",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 700,
                padding: "4px 8px",
                cursor: "pointer",
              }}
            >
              EN
            </button>
          </div>
        </div>

        {/* Live Audio Input Waveform Box */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-hairline)",
            padding: 14,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={() => {
                  const currentPrompts = samplePrompts[selectedLanguage];
                  const randomPrompt = currentPrompts[Math.floor(Math.random() * currentPrompts.length)];
                  handleSimulateVoice(randomPrompt.text, randomPrompt.pickup, randomPrompt.drop);
                }}
                style={{
                  width: 32,
                  height: 32,
                  background: isListening ? "var(--lime)" : "#000",
                  color: isListening ? "#000" : "var(--lime)",
                  border: "1px solid var(--lime)",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                  fontSize: 14,
                }}
                title="Tap to speak"
              >
                🎙
              </button>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: isListening ? "var(--lime)" : "#fff" }}>
                {isListening ? "LISTENING TO SPEECH…" : "SPEECH-TO-CAB DISPATCH"}
              </div>
            </div>

            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>
              ACCURACY 99.2%
            </span>
          </div>

          <div style={{ height: 44, width: "100%", overflow: "hidden" }}>
            <canvas ref={canvasRef} style={{ width: "100%", height: "100%" }} />
          </div>

          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: isListening ? "var(--lime)" : "var(--text-secondary)",
              background: "#0c0d12",
              padding: "8px 12px",
              border: "1px solid var(--border-hairline)",
            }}
          >
            {transcript}
          </div>
        </div>

        {/* Tap-to-Speak Prompt Shortcuts */}
        <div>
          <div className="stat-kicker">TRY COMMON BENGALURU VOICE PROMPTS</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {samplePrompts[selectedLanguage].map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSimulateVoice(prompt.text, prompt.pickup, prompt.drop)}
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-hairline)",
                  padding: "10px 14px",
                  textAlign: "left",
                  color: "var(--text-main)",
                  fontFamily: "var(--font-sans)",
                  fontSize: 12,
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  transition: "all 0.15s ease",
                }}
              >
                <span>{prompt.text}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--lime)" }}>
                  AUTO-SET ➔
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

