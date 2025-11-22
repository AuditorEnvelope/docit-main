"use client";

import { BookOpen, Search } from "lucide-react";
import { useMemo } from "react";

export const ONBOARDING_PROGRESS_MESSAGES = [
  "Checking Reader App installation…",
  "Verifying Writer App permissions…",
  "Confirming docbook linkage…",
  "Syncing organization metadata…",
  "Preparing dashboard experience…",
] as const;

type OnboardingSplashProps = {
  title?: string;
  messages?: readonly string[];
  activeIndex?: number;
};

export function OnboardingSplash({
  title = "Preparing your workspace",
  messages = ONBOARDING_PROGRESS_MESSAGES,
  activeIndex = 0,
}: OnboardingSplashProps) {
  const safeIndex = useMemo(() => {
    if (!messages.length) return 0;
    return ((activeIndex % messages.length) + messages.length) % messages.length;
  }, [activeIndex, messages.length]);

  const activeMessage = messages[safeIndex] ?? "";

  return (
    <>
      <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-slate-950 px-6 text-slate-200">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(17,28,63,0.55),_rgba(4,7,15,0.96))]"
          aria-hidden
        />
        <div className="aurora aurora-one" aria-hidden />
        <div className="aurora aurora-two" aria-hidden />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(56,189,248,0.15),transparent_55%),radial-gradient(circle_at_80%_80%,rgba(168,85,247,0.15),transparent_45%)]" aria-hidden />

        <div className="card-shell">
          <div className="book-orbit">
            <div className="book-stack">
              <span className="book-page" />
              <span className="book-page delay" />
              <span className="book-cover">
                <BookOpen className="h-14 w-14 text-indigo-100" />
              </span>
            </div>
            <div className="scan-lens">
              <Search className="h-7 w-7 text-blue-100" />
            </div>
          </div>

          <div className="space-y-4">
            <p className="text-2xl font-semibold text-white tracking-tight">{title}</p>
            {activeMessage ? (
              <div className="relative h-6 overflow-hidden text-slate-300/90">
                <span key={activeMessage} className="message-fade">
                  {activeMessage}
                </span>
              </div>
            ) : null}
          </div>

          {messages.length > 0 ? (
            <div className="w-full space-y-2">
              <div className="progress-track">
                <span className="progress-glow" />
              </div>
              <div className="flex items-center justify-center gap-3 text-xs tracking-[0.45em] text-slate-500">
                {messages.map((_, idx) => (
                  <span
                    key={idx}
                    className={`indicator ${idx === safeIndex ? "indicator-active" : ""}`}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <style jsx>{`
        .card-shell {
          position: relative;
          z-index: 10;
          display: flex;
          width: min(90vw, 420px);
          flex-direction: column;
          align-items: center;
          gap: 36px;
          border-radius: 28px;
          padding: 48px 44px;
          background: linear-gradient(170deg, rgba(7, 12, 28, 0.94) 0%, rgba(19, 17, 42, 0.95) 55%, rgba(3, 6, 15, 0.92) 100%);
          border: 1px solid rgba(76, 29, 149, 0.28);
          box-shadow: 0 44px 120px -70px rgba(59, 59, 185, 0.8), inset 0 0 45px -28px rgba(37, 99, 235, 0.28);
          backdrop-filter: blur(18px);
          animation: cardAppear 0.85s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .book-orbit {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 200px;
          height: 200px;
          animation: floatOrbit 6s ease-in-out infinite;
        }

        .book-stack {
          position: relative;
          width: 150px;
          height: 110px;
          border-radius: 32px;
          background: linear-gradient(140deg, rgba(99, 102, 241, 0.45), rgba(30, 64, 175, 0.3));
          box-shadow: 0 35px 75px -45px rgba(99, 102, 241, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
        }

        .book-page {
          position: absolute;
          inset: 18px;
          border-radius: 20px;
          background: rgba(148, 163, 184, 0.14);
          animation: pageFlip 2.6s ease-in-out infinite;
        }

        .book-page.delay {
          animation-delay: 1.3s;
        }

        .book-cover {
          position: relative;
          z-index: 2;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
          backdrop-filter: blur(16px);
          background: linear-gradient(150deg, rgba(79, 70, 229, 0.4), rgba(99, 102, 241, 0.55));
        }

        .scan-lens {
          position: absolute;
          inset: auto;
          width: 74px;
          height: 74px;
          border-radius: 999px;
          border: 1px solid rgba(129, 140, 248, 0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          background: radial-gradient(circle at 35% 35%, rgba(79, 70, 229, 0.33), rgba(15, 23, 42, 0.92));
          animation: orbit 7.2s linear infinite;
          box-shadow: 0 26px 45px -30px rgba(59, 130, 246, 0.65);
        }

        .progress-track {
          position: relative;
          width: 100%;
          height: 8px;
          border-radius: 999px;
          background: linear-gradient(90deg, rgba(51, 65, 85, 0.6), rgba(15, 23, 42, 0.8));
          overflow: hidden;
        }

        .progress-glow {
          position: absolute;
          inset: 0;
          width: 35%;
          border-radius: inherit;
          background: linear-gradient(90deg, rgba(59, 130, 246, 0.05), rgba(129, 140, 248, 0.55), rgba(45, 212, 191, 0.35));
          animation: progressSweep 2.4s ease-in-out infinite;
        }

        .indicator {
          display: inline-flex;
          height: 7px;
          width: 28px;
          border-radius: 999px;
          background: rgba(51, 65, 85, 0.7);
          transition: all 0.5s ease;
          overflow: hidden;
        }

        .indicator-active {
          background: linear-gradient(90deg, rgba(147, 197, 253, 0.35), rgba(165, 180, 252, 0.9));
          box-shadow: 0 0 18px rgba(99, 102, 241, 0.5);
        }

        .message-fade {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          animation: messageShift 0.85s ease forwards;
        }

        .aurora {
          position: absolute;
          inset: auto;
          width: 70vw;
          max-width: 900px;
          height: 70vw;
          max-height: 900px;
          filter: blur(120px);
          background: conic-gradient(from 180deg at 50% 50%, rgba(37, 99, 235, 0.16), rgba(109, 40, 217, 0.16), rgba(22, 163, 74, 0.08), rgba(37, 99, 235, 0.16));
          pointer-events: none;
          animation: auroraDrift 18s ease-in-out infinite;
          opacity: 0.45;
        }

        .aurora-one {
          top: -30%;
          left: -25%;
          animation-delay: -5s;
        }

        .aurora-two {
          bottom: -35%;
          right: -20%;
          animation-delay: -11s;
        }

        @keyframes cardAppear {
          0% {
            transform: translateY(36px) scale(0.95);
            opacity: 0;
          }
          100% {
            transform: translateY(0) scale(1);
            opacity: 1;
          }
        }

        @keyframes floatOrbit {
          0%,
          100% {
            transform: translateY(-6px);
          }
          50% {
            transform: translateY(6px);
          }
        }

        @keyframes pageFlip {
          0%,
          100% {
            transform: rotateY(0deg);
            opacity: 0.55;
          }
          50% {
            transform: rotateY(-32deg) translateX(-8px);
            opacity: 1;
          }
        }

        @keyframes orbit {
          0% {
            transform: rotate(0deg) translateX(94px) rotate(0deg);
          }
          50% {
            transform: rotate(180deg) translateX(94px) rotate(-180deg);
          }
          100% {
            transform: rotate(360deg) translateX(94px) rotate(-360deg);
          }
        }

        @keyframes progressSweep {
          0% {
            transform: translateX(-110%);
          }
          50% {
            transform: translateX(15%);
          }
          100% {
            transform: translateX(110%);
          }
        }

        @keyframes messageShift {
          0% {
            transform: translateY(16px);
            opacity: 0;
          }
          40% {
            transform: translateY(0);
            opacity: 1;
          }
          100% {
            transform: translateY(0);
            opacity: 1;
          }
        }

        @keyframes auroraDrift {
          0%,
          100% {
            transform: rotate(0deg) scale(1);
          }
          50% {
            transform: rotate(20deg) scale(1.05);
          }
        }
      `}</style>
    </>
  );
}
