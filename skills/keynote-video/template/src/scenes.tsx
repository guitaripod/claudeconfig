import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Rise, reveal} from './anim';
import {AppIcon, Callout, Copy, Device, gradientText} from './parts';
import {BRAND_GRADIENT, DIM, FAINT, INK, SANS, useLayout} from './theme';
import {local} from './timing';

interface SceneProps {
  len: number;
}

const Centered: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily: SANS}}>{children}</AbsoluteFill>
);

export const OpenScene: React.FC<SceneProps> = () => {
  const {u, square} = useLayout();
  const frame = useCurrentFrame();
  const dim = reveal(frame, local(3), 20);
  return (
    <Centered>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '0 80px'}}>
        <div style={{opacity: 1 - 0.64 * dim}}>
          <Rise at={8}>
            <div style={{fontSize: 96 * u, fontWeight: 800, letterSpacing: '-0.035em', lineHeight: 1.08, color: INK}}>
              The problem, said in one line,
            </div>
          </Rise>
          <Rise at={20}>
            <div style={{fontSize: 96 * u, fontWeight: 800, letterSpacing: '-0.035em', lineHeight: 1.08, color: INK}}>
              that the viewer already feels.
            </div>
          </Rise>
        </div>
        <Rise at={local(3)} duration={36} style={{marginTop: (square ? 40 : 56) * u}}>
          <div style={{fontSize: 210 * u, fontWeight: 900, letterSpacing: '-0.045em', lineHeight: 1, ...gradientText}}>
            The turn.
          </div>
        </Rise>
      </div>
    </Centered>
  );
};

export const TitleScene: React.FC<SceneProps> = () => {
  const {u, square} = useLayout();
  return (
    <Centered>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center'}}>
        <AppIcon size={square ? 190 : 250} at={0} />
        <Rise at={local(1) - 6} style={{marginTop: 44 * u}}>
          <div style={{fontSize: 200 * u, fontWeight: 900, letterSpacing: '-0.05em', lineHeight: 1, color: INK}}>
            App Name
          </div>
        </Rise>
        <Rise at={local(2)} style={{marginTop: 30 * u}}>
          <div style={{fontSize: 54 * Math.max(u, 0.78), fontWeight: 700, color: DIM, letterSpacing: '-0.02em'}}>
            What it works with.
          </div>
        </Rise>
        <Rise at={local(3)} style={{marginTop: 8 * u}}>
          <div style={{fontSize: 54 * Math.max(u, 0.78), fontWeight: 800, letterSpacing: '-0.02em', ...gradientText}}>
            Where it works.
          </div>
        </Rise>
      </div>
    </Centered>
  );
};

interface SplitProps {
  side: 'left' | 'right';
  copy: React.ReactNode;
  device: React.ReactNode;
  deviceTop?: number;
}

const Split: React.FC<SplitProps> = ({side, copy, device, deviceTop}) => {
  const {square, margin, height} = useLayout();
  if (square) {
    return (
      <AbsoluteFill style={{fontFamily: SANS}}>
        <div style={{position: 'absolute', left: margin, right: margin, top: 70}}>{copy}</div>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: -110, display: 'flex', justifyContent: 'center'}}>
          {device}
        </div>
      </AbsoluteFill>
    );
  }
  const text = <div style={{flex: 1, display: 'flex', alignItems: 'center'}}>{copy}</div>;
  const dev = (
    <div
      style={{
        width: 760,
        display: 'flex',
        alignItems: deviceTop === undefined ? 'center' : 'flex-start',
        justifyContent: 'center',
        height,
        paddingTop: deviceTop ?? 0,
      }}
    >
      {device}
    </div>
  );
  return (
    <AbsoluteFill style={{fontFamily: SANS, display: 'flex', flexDirection: 'row', alignItems: 'center', padding: `0 ${margin}px`}}>
      {side === 'right' ? (
        <>
          {text}
          {dev}
        </>
      ) : (
        <>
          {dev}
          <div style={{width: 40}} />
          {text}
        </>
      )}
    </AbsoluteFill>
  );
};

export const DeviceScene: React.FC<SceneProps> = ({len}) => {
  const {square} = useLayout();
  const height = square ? 800 : 1120;
  return (
    <Split
      side="right"
      deviceTop={50}
      copy={
        <Copy
          kicker="Feature"
          lines={[
            {text: 'The benefit,', at: 10},
            {text: 'in four words.', at: local(1), accent: true},
          ]}
          sub="One sentence from the shipped store caption, never invented."
          subAt={local(3)}
        />
      }
      device={
        <Device src="framed/shot1.png" height={height} len={len}>
          <Callout deviceHeight={height} targets={[{rect: [35, 425, 552, 638], at: local(2), until: local(5), radius: 36}]} />
        </Device>
      }
    />
  );
};

export const EndScene: React.FC<SceneProps> = () => {
  const {u, square} = useLayout();
  const frame = useCurrentFrame();
  const pill = reveal(frame, local(2), 30);
  const k = Math.max(u, 0.8);
  return (
    <Centered>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center'}}>
        <AppIcon size={square ? 150 : 190} at={0} />
        <Rise at={10} style={{marginTop: 30 * u}}>
          <div style={{fontSize: 150 * u, fontWeight: 900, letterSpacing: '-0.05em', lineHeight: 1, color: INK}}>App Name</div>
        </Rise>
        <Rise at={local(1)} style={{marginTop: 26 * u}}>
          <div style={{fontSize: 70 * k, fontWeight: 800, letterSpacing: '-0.03em', color: INK}}>The call to action.</div>
        </Rise>
        <div
          style={{
            marginTop: 46 * u,
            padding: `${22 * k}px ${54 * k}px`,
            borderRadius: 999,
            background: BRAND_GRADIENT,
            opacity: pill,
            transform: `translateY(${(1 - pill) * 24}px) scale(${0.96 + 0.04 * pill})`,
            boxShadow: '0 20px 70px rgba(76,107,255,0.45)',
          }}
        >
          <div style={{fontSize: 62 * k, fontWeight: 800, letterSpacing: '-0.025em', color: '#FFFFFF'}}>example.com/app</div>
        </div>
        <Rise at={local(3)} style={{marginTop: 40 * u}}>
          <div style={{fontSize: 32 * k, fontWeight: 500, color: FAINT}}>Platforms, price, licence.</div>
        </Rise>
      </div>
    </Centered>
  );
};
