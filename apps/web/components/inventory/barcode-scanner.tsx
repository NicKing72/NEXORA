"use client";

import { Camera, CameraOff, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { stopMediaStream } from "@/lib/kardex-state";

type DetectorResult = { rawValue: string };
type Detector = { detect: (source: HTMLVideoElement) => Promise<DetectorResult[]> };
type DetectorConstructor = new (options?: { formats?: string[] }) => Detector;
type ScannerControls = { stop: () => void };

export function BarcodeScanner({ onDetected }: { onDetected: (value: string) => void }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("Cámara inactiva");
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const controlsRef = useRef<ScannerControls | null>(null);
  const frameRef = useRef<number | null>(null);
  const detectedRef = useRef(onDetected);

  useEffect(() => {
    detectedRef.current = onDetected;
  }, [onDetected]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    const videoElement = videoRef.current;
    async function start() {
      setError(null);
      setStatus("Solicitando permiso de cámara…");
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new DOMException("Camera API unavailable", "NotFoundError");
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        if (!active) {
          stopMediaStream(stream);
          return;
        }
        streamRef.current = stream;
        const video = videoElement;
        if (!video) return;
        video.srcObject = stream;
        await video.play();
        setStatus("Buscando código…");
        const NativeDetector = (globalThis as typeof globalThis & {
          BarcodeDetector?: DetectorConstructor;
        }).BarcodeDetector;
        const detected = (value: string) => {
          if (!active || !value) return;
          setStatus(`Código detectado: ${value}`);
          detectedRef.current(value);
          setOpen(false);
        };
        if (NativeDetector) {
          try {
            const detector = new NativeDetector({
              formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "qr_code"],
            });
            const scan = async () => {
              if (!active || video.readyState < 2) return;
              const results = await detector.detect(video).catch(() => []);
              if (results[0]?.rawValue) detected(results[0].rawValue);
              else frameRef.current = requestAnimationFrame(scan);
            };
            frameRef.current = requestAnimationFrame(scan);
            return;
          } catch {
            // A partial native implementation falls through to the bundled local decoder.
          }
        }
        const { BrowserMultiFormatReader } = await import("@zxing/browser");
        const reader = new BrowserMultiFormatReader();
        const controls = await reader.decodeFromStream(stream, video, (result) => {
          if (result) detected(result.getText());
        });
        if (active) controlsRef.current = controls;
        else controls.stop();
      } catch (cause) {
        const name = cause instanceof DOMException ? cause.name : "";
        setError(name === "NotAllowedError"
          ? "Permiso de cámara denegado. Puedes usar el lector USB o escribir el código."
          : "No se encontró una cámara compatible. Puedes usar el lector USB o escribir el código.");
        setStatus("Cámara no disponible");
      }
    }
    void start();
    return () => {
      active = false;
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      controlsRef.current?.stop();
      controlsRef.current = null;
      stopMediaStream(streamRef.current);
      streamRef.current = null;
      if (videoElement) videoElement.srcObject = null;
    };
  }, [open]);

  return (
    <>
      <button className="kd-secondary" type="button" onClick={() => setOpen(true)}>
        <Camera size={17} /> Escanear código
      </button>
      {open && (
        <div className="kd-modal-backdrop" role="presentation">
          <section className="kd-scanner" role="dialog" aria-modal="true" aria-label="Escáner de código">
            <header><div><span>Lectura local</span><h2>Escanear código</h2></div><button type="button" aria-label="Cerrar escáner" onClick={() => setOpen(false)}><X size={20} /></button></header>
            <div className="kd-camera-frame"><video ref={videoRef} muted playsInline /><div className="kd-scan-line" /></div>
            <p className="kd-camera-status">{error ? <CameraOff size={16} /> : <Camera size={16} />}{error ?? status}</p>
            <small>El video se procesa localmente. NEXORA no guarda ni envía imágenes.</small>
          </section>
        </div>
      )}
    </>
  );
}
