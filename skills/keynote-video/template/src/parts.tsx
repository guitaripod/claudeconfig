import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {reveal, fadeOut, Rise} from './anim';
import {ACCENT, BRAND_GRADIENT, DIM, INK, SANS, useLayout} from './theme';
import {FPS, TOTAL} from './timing';

export const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const progress = frame / TOTAL;
  const blueX = 24 + 10 * Math.sin(t * 0.35);
  const blueY = 30 + 8 * Math.cos(t * 0.27);
  const violetX = 78 + 9 * Math.cos(t * 0.31);
  const violetY = 74 + 8 * Math.sin(t * 0.23);
  const violetWeight = 0.14 + 0.1 * progress;
  return (
    <AbsoluteFill
      style={{
        background: [
          `radial-gradient(1100px 800px at ${blueX}% ${blueY}%, rgba(76,141,255,0.20), transparent 62%)`,
          `radial-gradient(1000px 800px at ${violetX}% ${violetY}%, rgba(124,58,237,${violetWeight}), transparent 62%)`,
          '#06070B',
        ].join(', '),
      }}
    />
  );
};

export const gradientText: React.CSSProperties = {
  background: BRAND_GRADIENT,
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  color: 'transparent',
};

export interface CopyLine {
  text: string;
  at: number;
  accent?: boolean;
  dimAt?: number;
}

interface CopyProps {
  kicker?: string;
  kickerAt?: number;
  lines: CopyLine[];
  sub?: string;
  subAt?: number;
  size?: number;
  align?: 'left' | 'center';
}

export const Copy: React.FC<CopyProps> = ({kicker, kickerAt = 4, lines, sub, subAt = 60, size = 104, align = 'left'}) => {
  const {u} = useLayout();
  const frame = useCurrentFrame();
  const alignItems = align === 'center' ? 'center' : 'flex-start';
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems, textAlign: align, fontFamily: SANS}}>
      {kicker ? (
        <Rise at={kickerAt} blur={0} rise={16}>
          <div
            style={{
              color: ACCENT,
              fontSize: 27 * Math.max(u, 0.8),
              fontWeight: 800,
              letterSpacing: '0.24em',
              textTransform: 'uppercase',
              marginBottom: 28 * u,
            }}
          >
            {kicker}
          </div>
        </Rise>
      ) : null}
      {lines.map((line) => {
        const dim = line.dimAt === undefined ? 0 : reveal(frame, line.dimAt, 20);
        return (
          <Rise key={line.text} at={line.at}>
            <div
              style={{
                fontSize: size * u,
                fontWeight: 900,
                lineHeight: 1.04,
                letterSpacing: '-0.036em',
                opacity: 1 - 0.62 * dim,
                whiteSpace: 'nowrap',
                color: INK,
                ...(line.accent ? gradientText : {}),
              }}
            >
              {line.text}
            </div>
          </Rise>
        );
      })}
      {sub ? (
        <Rise at={subAt} rise={20} blur={8}>
          <div
            style={{
              marginTop: 38 * u,
              color: DIM,
              fontSize: 40 * Math.max(u, 0.78),
              fontWeight: 500,
              lineHeight: 1.32,
              maxWidth: 900 * (u < 1 ? 1.05 : 1),
              letterSpacing: '-0.01em',
            }}
          >
            {sub}
          </div>
        </Rise>
      ) : null}
    </div>
  );
};

interface DeviceProps {
  src: string;
  height?: number;
  width?: number;
  at?: number;
  len: number;
  push?: number;
  fadeAt?: number;
  fadeFrames?: number;
  glow?: boolean;
  children?: React.ReactNode;
}

export const Device: React.FC<DeviceProps> = ({
  src,
  height,
  width,
  at = 6,
  len,
  push = 0.05,
  fadeAt,
  fadeFrames = 18,
  glow = true,
  children,
}) => {
  const frame = useCurrentFrame();
  const progress = reveal(frame, at, 38);
  const scale = 0.95 + 0.05 * progress + push * (frame / len);
  const out = fadeAt === undefined ? 1 : fadeOut(frame, fadeAt, fadeFrames);
  return (
    <div
      style={{
        position: 'relative',
        height,
        width,
        opacity: progress * out,
        transform: `translateY(${(1 - progress) * 80}px) scale(${scale})`,
      }}
    >
      {glow ? (
        <div
          style={{
            position: 'absolute',
            inset: '6% -14%',
            borderRadius: '50%',
            background: BRAND_GRADIENT,
            opacity: 0.2,
            filter: 'blur(110px)',
          }}
        />
      ) : null}
      <Img
        src={staticFile(src)}
        style={{
          position: 'relative',
          height: height ? '100%' : undefined,
          width: width ? '100%' : undefined,
          display: 'block',
          filter: 'drop-shadow(0 50px 70px rgba(10,16,60,0.55))',
        }}
      />
      {children}
    </div>
  );
};

const SCREEN_UNITS_TO_PIXELS = 1320 / 921;
const BEZEL_X = 75;
const BEZEL_Y = 66;
const FRAMED_HEIGHT = 3000;

export interface RingTarget {
  rect: [number, number, number, number];
  at: number;
  until?: number;
  radius?: number;
}

/**
 * Highlight rings placed in the coordinates of a 921x2000 view of an iPhone master,
 * so a target can be read straight off the screenshot as it is displayed.
 */
export const Callout: React.FC<{deviceHeight: number; targets: RingTarget[]}> = ({deviceHeight, targets}) => {
  const frame = useCurrentFrame();
  const k = deviceHeight / FRAMED_HEIGHT;
  const px = (units: number, bezel: number): number => (units * SCREEN_UNITS_TO_PIXELS + bezel) * k;
  return (
    <>
      {targets.map(({rect: [x0, y0, x1, y1], at, until, radius = 26}) => {
        const appear = reveal(frame, at, 22);
        const out = until === undefined ? 1 : fadeOut(frame, until, 16);
        const pulse = 0.5 + 0.5 * Math.sin((frame - at) / 9);
        return (
          <div
            key={`${x0}-${y0}-${at}`}
            style={{
              position: 'absolute',
              left: px(x0, BEZEL_X),
              top: px(y0, BEZEL_Y),
              width: (x1 - x0) * SCREEN_UNITS_TO_PIXELS * k,
              height: (y1 - y0) * SCREEN_UNITS_TO_PIXELS * k,
              borderRadius: radius * SCREEN_UNITS_TO_PIXELS * k,
              border: '4px solid rgba(150,196,255,0.95)',
              background: 'rgba(76,141,255,0.08)',
              boxShadow: `0 0 0 ${4 + 6 * pulse}px rgba(125,180,255,0.16), 0 0 46px rgba(76,141,255,0.65)`,
              opacity: appear * out,
              transform: `scale(${1.05 - 0.05 * appear})`,
              pointerEvents: 'none',
            }}
          />
        );
      })}
    </>
  );
};

export const LinuxWindow: React.FC<{
  height?: number;
  width?: number;
  at?: number;
  len: number;
  fadeAt?: number;
  fadeFrames?: number;
}> = ({height, width, at = 6, len, fadeAt, fadeFrames = 18}) => {
  const frame = useCurrentFrame();
  const progress = reveal(frame, at, 38);
  const scale = 0.95 + 0.05 * progress + 0.04 * (frame / len);
  const out = fadeAt === undefined ? 1 : fadeOut(frame, fadeAt, fadeFrames);
  const aspect = 2560 / 1440;
  const w = width ?? (height as number) * aspect;
  const h = height ?? (width as number) / aspect;
  return (
    <div
      style={{
        position: 'relative',
        width: w,
        height: h,
        opacity: progress * out,
        transform: `translateY(${(1 - progress) * 80}px) scale(${scale})`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: '6% -10%',
          borderRadius: '50%',
          background: BRAND_GRADIENT,
          opacity: 0.18,
          filter: 'blur(100px)',
        }}
      />
      <Img
        src={staticFile('raw/linux-columns.png')}
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          borderRadius: Math.round(w * 0.012),
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: '0 50px 90px rgba(5,8,40,0.6)',
          display: 'block',
        }}
      />
    </div>
  );
};

export const AppIcon: React.FC<{size: number; at?: number}> = ({size, at = 0}) => {
  const frame = useCurrentFrame();
  const progress = reveal(frame, at, 36);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.225,
        overflow: 'hidden',
        opacity: progress,
        transform: `scale(${0.82 + 0.18 * progress}) translateY(${(1 - progress) * 40}px)`,
        boxShadow: '0 30px 80px rgba(60,80,255,0.45)',
      }}
    >
      <Img src={staticFile('AppIcon.svg')} style={{width: '100%', height: '100%', display: 'block'}} />
    </div>
  );
};
