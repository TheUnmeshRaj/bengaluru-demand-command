"use client";

import { useEffect, useRef } from "react";

export default function AcousticNoiseVisualizer() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animRef = useRef<number | null>(null);
  const phaseRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = canvas.parentElement?.clientWidth || 300);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 90);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener("resize", handleResize);

    const render = () => {
      ctx.fillStyle = "rgba(7, 9, 14, 0.3)";
      ctx.fillRect(0, 0, width, height);

      // Draw oscilloscope grid lines
      ctx.strokeStyle = "rgba(40, 50, 70, 0.4)";
      ctx.lineWidth = 1;

      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();

      // Draw animated acoustic waveform
      phaseRef.current += 0.05;
      const phase = phaseRef.current;

      ctx.beginPath();
      ctx.strokeStyle = "var(--lime)";
      ctx.lineWidth = 1.8;

      for (let x = 0; x < width; x++) {
        // Multi-frequency harmonic wave simulating rotor signature
        const y =
          height / 2 +
          Math.sin(x * 0.04 + phase) * 16 +
          Math.sin(x * 0.1 - phase * 1.5) * 8 +
          Math.sin(x * 0.02 + phase * 0.8) * 6;

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      animRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, []);

  return (
    <div className="bento-body">
      <div className="oscilloscope-box">
        <canvas ref={canvasRef} className="oscilloscope-canvas" />
      </div>

      <div className="acoustic-stats-row">
        <div>
          <span style={{ color: "var(--text-muted)" }}>CABIN ACOUSTIC LEVEL</span>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 16,
              fontWeight: 800,
              color: "var(--lime)",
              marginTop: 2,
            }}
          >
            62 dBA <span style={{ fontSize: 10, color: "#9da8b9" }}>[WHISPER-TIER]</span>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <span style={{ color: "var(--text-muted)" }}>STREET AMBIENT NOISE</span>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 16,
              fontWeight: 800,
              color: "#ffaa00",
              marginTop: 2,
            }}
          >
            85 dBA <span style={{ fontSize: 10, color: "#9da8b9" }}>[GRIDLOCK]</span>
          </div>
        </div>
      </div>

      <div
        style={{
          marginTop: 12,
          padding: 8,
          background: "#080a0f",
          border: "1px solid var(--border-subtle)",
          fontFamily: "var(--font-mono)",
          fontSize: 9,
          color: "var(--text-secondary)",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span>CITY NOISE CODE §12-B: COMPLIANT</span>
        <span style={{ color: "var(--lime)" }}>-23 dB QUIETER THAN TRAFFIC</span>
      </div>
    </div>
  );
}

