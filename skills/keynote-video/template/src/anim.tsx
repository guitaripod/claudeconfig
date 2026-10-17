import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';

const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

export const reveal = (frame: number, at: number, duration = 30): number =>
  interpolate(frame, [at, at + duration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_OUT,
  });

export const fadeOut = (frame: number, at: number, duration = 14): number =>
  interpolate(frame, [at, at + duration], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

interface RiseProps {
  at: number;
  duration?: number;
  rise?: number;
  blur?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}

export const Rise: React.FC<RiseProps> = ({at, duration = 30, rise = 34, blur = 14, style, children}) => {
  const frame = useCurrentFrame();
  const progress = reveal(frame, at, duration);
  return (
    <div
      style={{
        opacity: progress,
        transform: `translateY(${(1 - progress) * rise}px)`,
        filter: blur > 0 && progress < 1 ? `blur(${(1 - progress) * blur}px)` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const FadeOutAt: React.FC<{at: number; duration?: number; children: React.ReactNode}> = ({
  at,
  duration = 14,
  children,
}) => {
  const frame = useCurrentFrame();
  return <div style={{opacity: fadeOut(frame, at, duration), width: '100%'}}>{children}</div>;
};
