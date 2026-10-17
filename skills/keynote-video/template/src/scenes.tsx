import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {FadeOutAt, Rise, reveal} from './anim';
import {AppIcon, Callout, Copy, Device, LinuxWindow, gradientText} from './parts';
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
              Your coding agent runs on
            </div>
          </Rise>
          <Rise at={20}>
            <div style={{fontSize: 96 * u, fontWeight: 800, letterSpacing: '-0.035em', lineHeight: 1.08, color: INK}}>
              the machine with your code.
            </div>
          </Rise>
        </div>
        <Rise at={local(3)} duration={36} style={{marginTop: (square ? 40 : 56) * u}}>
          <div style={{fontSize: 210 * u, fontWeight: 900, letterSpacing: '-0.045em', lineHeight: 1, ...gradientText}}>
            You don’t.
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
            Tailscode
          </div>
        </Rise>
        <Rise at={local(2)} style={{marginTop: 30 * u}}>
          <div style={{fontSize: 54 * Math.max(u, 0.78), fontWeight: 700, color: DIM, letterSpacing: '-0.02em'}}>
            Claude Code. opencode. Oh My Pi.
          </div>
        </Rise>
        <Rise at={local(3)} style={{marginTop: 8 * u}}>
          <div style={{fontSize: 54 * Math.max(u, 0.78), fontWeight: 800, letterSpacing: '-0.02em', ...gradientText}}>
            From anywhere.
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
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: -110,
            display: 'flex',
            justifyContent: 'center',
          }}
        >
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
    <AbsoluteFill
      style={{
        fontFamily: SANS,
        flexDirection: 'row',
        padding: `0 ${margin}px`,
        display: 'flex',
        alignItems: 'center',
      }}
    >
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

const phoneHeight = (square: boolean) => (square ? 800 : 960);
const bleedHeight = (square: boolean) => (square ? 800 : 1120);
const BLEED_TOP = 50;

export const LockScene: React.FC<SceneProps> = ({len}) => {
  const {square} = useLayout();
  const swap = local(5);
  const h = phoneHeight(square);
  const hb = bleedHeight(square);
  return (
    <Split
      side="right"
      deviceTop={BLEED_TOP}
      copy={
        <div style={{position: 'relative', width: '100%', minHeight: square ? 330 : 520}}>
          <Sequence from={0} durationInFrames={swap + 16} layout="none">
            <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: square ? 'flex-start' : 'center'}}>
              <FadeOutAt at={swap}>
                <Copy
                  kicker="Lock Screen"
                  lines={[
                    {text: 'Send. Pocket it.', at: 10},
                    {text: 'Get pinged.', at: local(2), accent: true},
                  ]}
                  sub="Your coding agents, live on the Lock Screen, over your own tailnet."
                  subAt={local(3)}
                />
              </FadeOutAt>
            </div>
          </Sequence>
          <Sequence from={swap} layout="none">
            <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: square ? 'flex-start' : 'center'}}>
              <Copy
                kicker="Approvals"
                lines={[
                  {text: 'Approve the', at: 4},
                  {text: 'risky command.', at: local(1), accent: true},
                ]}
                sub="Allow once, always or deny, while the agent waits."
                subAt={local(2)}
              />
            </div>
          </Sequence>
        </div>
      }
      device={
        <div style={{position: 'relative', height: hb, width: hb * (1470 / 3000)}}>
          <div style={{position: 'absolute', left: ((hb - h) * (1470 / 3000)) / 2, top: square ? (hb - h) / 2 : 10}}>
            <Device src="framed/lock_framed.png" height={h} len={len} fadeAt={swap}>
              <Callout deviceHeight={h} targets={[{rect: [45, 1498, 877, 1665], at: local(2.5), radius: 40}]} />
            </Device>
          </div>
          <Sequence from={swap} layout="none">
            <div style={{position: 'absolute', inset: 0}}>
              <Device src="framed/03-approval_framed.png" height={hb} len={len - swap} at={0} push={0.04}>
                <Callout
                  deviceHeight={hb}
                  targets={[
                    {rect: [34, 1182, 886, 1633], at: local(1.5), until: local(3.2), radius: 40},
                    {rect: [58, 1328, 862, 1411], at: local(3.2), radius: 36},
                  ]}
                />
              </Device>
            </div>
          </Sequence>
        </div>
      }
    />
  );
};

export const BoardScene: React.FC<SceneProps> = ({len}) => {
  const {square} = useLayout();
  return (
    <Split
      side="left"
      copy={
        <Copy
          kicker="One board"
          lines={[
            {text: 'Every machine,', at: 10},
            {text: 'one board.', at: local(1), accent: true},
          ]}
          sub="Live turns first, grouped by project, across all your servers."
          subAt={local(3)}
        />
      }
      deviceTop={BLEED_TOP}
      device={
        <Device src="framed/07-home_framed.png" height={bleedHeight(square)} len={len}>
          <Callout
            deviceHeight={bleedHeight(square)}
            targets={[
              {rect: [35, 425, 552, 638], at: local(2), until: local(4.6), radius: 36},
              {rect: [35, 745, 918, 928], at: local(4.6), until: local(7), radius: 36},
              {rect: [35, 1035, 886, 1645], at: local(7), radius: 36},
            ]}
          />
        </Device>
      }
    />
  );
};

export const DiffScene: React.FC<SceneProps> = ({len}) => {
  const {square} = useLayout();
  return (
    <Split
      side="right"
      copy={
        <Copy
          kicker="The diff"
          lines={[
            {text: 'Read every diff', at: 10},
            {text: 'from your phone.', at: local(1), accent: true},
          ]}
          sub="The real patch, from the machine that owns it."
          subAt={local(3)}
        />
      }
      deviceTop={BLEED_TOP}
      device={
        <Device src="framed/13-diff_framed.png" height={bleedHeight(square)} len={len}>
          <Callout
            deviceHeight={bleedHeight(square)}
            targets={[
              {rect: [10, 753, 911, 1246], at: local(2), until: local(5.5), radius: 16},
              {rect: [10, 340, 911, 396], at: local(5.5), radius: 16},
            ]}
          />
        </Device>
      }
    />
  );
};

interface ClientSpec {
  word: string;
  aspect: number;
  render: (props: {height: number; at: number; len: number; fadeAt?: number; fadeFrames?: number}) => React.ReactNode;
}

const CLIENTS: ClientSpec[] = [
  {
    word: 'iPhone.',
    aspect: 1470 / 3000,
    render: ({height, at, len, fadeAt, fadeFrames}) => (
      <Device src="framed/07-home_framed.png" height={height} at={at} len={len} fadeAt={fadeAt} fadeFrames={fadeFrames} push={0.03} />
    ),
  },
  {
    word: 'iPad.',
    aspect: 3000 / 2300,
    render: ({height, at, len, fadeAt, fadeFrames}) => (
      <Device src="framed/ipad-approval_framed.png" height={height} at={at} len={len} fadeAt={fadeAt} fadeFrames={fadeFrames} push={0.03} />
    ),
  },
  {
    word: 'Mac.',
    aspect: 3800 / 2260,
    render: ({height, at, len, fadeAt, fadeFrames}) => (
      <Device src="framed/mac-split_framed.png" height={height} at={at} len={len} fadeAt={fadeAt} fadeFrames={fadeFrames} push={0.03} />
    ),
  },
  {
    word: 'Linux.',
    aspect: 2560 / 1440,
    render: ({height, at, len, fadeAt, fadeFrames}) => (
      <LinuxWindow height={height} at={at} len={len} fadeAt={fadeAt} fadeFrames={fadeFrames} />
    ),
  },
];

export const ClientsScene: React.FC<SceneProps> = ({len}) => {
  const {u, square, width, height} = useLayout();
  const frame = useCurrentFrame();
  const rowStart = local(8);
  const stageHeight = square ? 620 : 780;
  const rowHeight = square ? 160 : 310;
  const rowGap = square ? 24 : 50;
  const rowWidth = CLIENTS.reduce((sum, c) => sum + c.aspect * rowHeight, 0) + rowGap * (CLIENTS.length - 1);
  const stageTop = square ? 250 : 215;
  const activeIndex = (): number => {
    if (frame >= local(6)) return 3;
    if (frame >= local(4)) return 2;
    if (frame >= local(2)) return 1;
    return 0;
  };
  const active = frame >= rowStart ? -1 : activeIndex();
  return (
    <AbsoluteFill style={{fontFamily: SANS}}>
      <div
        style={{
          position: 'absolute',
          top: square ? 80 : 64,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          gap: 30 * u,
        }}
      >
        {CLIENTS.map((client, i) => {
          const lit = active === -1 ? 1 : i === active ? 1 : 0.28;
          return (
            <Rise key={client.word} at={6 + i * 5} duration={26}>
              <div
                style={{
                  fontSize: 96 * u,
                  fontWeight: 900,
                  letterSpacing: '-0.04em',
                  color: INK,
                  opacity: lit,
                }}
              >
                {client.word}
              </div>
            </Rise>
          );
        })}
      </div>
      {CLIENTS.map((client, i) => {
        const from = local(2 * i);
        const to = i === 3 ? rowStart : local(2 * i + 2);
        const visible = to - from;
        const stageH = client.aspect > 1 ? (square ? 460 : stageHeight * 0.92) : stageHeight;
        const cappedH = client.aspect > 1 ? Math.min(stageH, (square ? 960 : 1280) / client.aspect) : stageH;
        return (
          <Sequence key={client.word} from={from} durationInFrames={visible + 12} layout="none">
            <div
              style={{
                position: 'absolute',
                top: stageTop,
                left: 0,
                right: 0,
                height: stageHeight,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {client.render({
                height: cappedH,
                at: i === 0 ? 6 : 8,
                len: visible + 12,
                fadeAt: visible - 6,
                fadeFrames: 12,
              })}
            </div>
          </Sequence>
        );
      })}
      <Sequence from={rowStart} layout="none">
        <RowOfFour rowHeight={rowHeight} rowGap={rowGap} rowWidth={rowWidth} width={width} height={height} len={len - rowStart} />
      </Sequence>
    </AbsoluteFill>
  );
};

const RowOfFour: React.FC<{
  rowHeight: number;
  rowGap: number;
  rowWidth: number;
  width: number;
  height: number;
  len: number;
}> = ({rowHeight, rowGap, len}) => {
  const {u, square} = useLayout();
  const frame = useCurrentFrame();
  const intro = reveal(frame, 6, 30);
  return (
    <AbsoluteFill style={{opacity: intro}}>
      <div
        style={{
          position: 'absolute',
          top: square ? 330 : 300,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: rowGap,
        }}
      >
        {CLIENTS.map((client, i) => (
          <div key={client.word} style={{transform: `scale(${0.92 + 0.08 * reveal(frame, i * 4, 26)})`, opacity: reveal(frame, i * 4, 22)}}>
            {client.render({height: rowHeight, at: 0, len})}
          </div>
        ))}
      </div>
      <Rise at={14} style={{position: 'absolute', left: 0, right: 0, top: square ? 640 : 700, textAlign: 'center'}}>
        <div style={{fontSize: 64 * Math.max(u, 0.8), fontWeight: 800, letterSpacing: '-0.03em', color: INK}}>
          Native on each. <span style={gradientText}>One Swift core.</span>
        </div>
        <div style={{marginTop: 14, fontSize: 38 * Math.max(u, 0.8), fontWeight: 500, color: DIM}}>
          No cross-platform framework.
        </div>
      </Rise>
    </AbsoluteFill>
  );
};

const PrivateDiagram: React.FC<{width: number}> = ({width}) => {
  const frame = useCurrentFrame();
  const scale = width / 900;
  const strikes = [local(0) + 14, local(2), local(4)];
  const chips = [
    {label: 'relay', x: 130},
    {label: 'account', x: 345},
    {label: 'backend', x: 585},
  ];
  const lineProgress = reveal(frame, local(1), 60);
  const pulse = ((frame - local(3)) / 70) % 1;
  const pulseX = 150 + 600 * Math.max(0, pulse);
  const pulseOpacity = frame > local(3) ? Math.sin(Math.max(0, pulse) * Math.PI) : 0;
  const lineLabel = reveal(frame, local(4) + 10, 24);
  return (
    <svg width={width} height={560 * scale} viewBox="0 0 900 560" style={{fontFamily: SANS, overflow: 'visible'}}>
      <defs>
        <linearGradient id="link" gradientUnits="userSpaceOnUse" x1="190" y1="0" x2="710" y2="0">
          <stop offset="0" stopColor="#7DB4FF" />
          <stop offset="0.5" stopColor="#4C6BFF" />
          <stop offset="1" stopColor="#9B6BFF" />
        </linearGradient>
        <filter id="soft" filterUnits="userSpaceOnUse" x="100" y="340" width="700" height="120">
          <feGaussianBlur stdDeviation="9" />
        </filter>
      </defs>
      {chips.map((chip, i) => {
        const appear = reveal(frame, 4 + i * 4, 22);
        const struck = reveal(frame, strikes[i], 14);
        const gone = reveal(frame, strikes[i] + 6, 24);
        return (
          <g key={chip.label} opacity={appear * (1 - 0.7 * gone)} transform={`translate(0 ${gone * 12})`}>
            <rect x={chip.x} y={60} rx={34} width={190} height={68} fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.22)" />
            <text x={chip.x + 95} y={104} textAnchor="middle" fontSize={32} fontWeight={700} fill={INK}>
              {chip.label}
            </text>
            <line x1={chip.x + 18} y1={94} x2={chip.x + 18 + 154 * struck} y2={94} stroke="#FF5C7A" strokeWidth={5} strokeLinecap="round" />
          </g>
        );
      })}
      <g opacity={reveal(frame, 2, 24)}>
        <rect x={50} y={300} rx={34} width={130} height={200} fill="rgba(255,255,255,0.10)" stroke="rgba(255,255,255,0.5)" strokeWidth={3} />
        <rect x={64} y={322} rx={16} width={102} height={140} fill="rgba(76,141,255,0.18)" />
        <text x={115} y={540} textAnchor="middle" fontSize={26} fontWeight={700} fill={DIM}>
          your device
        </text>
      </g>
      <g opacity={reveal(frame, 6, 24)}>
        <rect x={720} y={300} rx={22} width={150} height={200} fill="rgba(255,255,255,0.10)" stroke="rgba(255,255,255,0.5)" strokeWidth={3} />
        <rect x={742} y={326} rx={8} width={106} height={26} fill="rgba(124,58,237,0.35)" />
        <rect x={742} y={366} rx={8} width={106} height={26} fill="rgba(76,141,255,0.30)" />
        <rect x={742} y={406} rx={8} width={106} height={26} fill="rgba(76,141,255,0.20)" />
        <text x={795} y={540} textAnchor="middle" fontSize={26} fontWeight={700} fill={DIM}>
          your machine
        </text>
      </g>
      <line x1={190} y1={400} x2={190 + 520 * lineProgress} y2={400} stroke="url(#link)" strokeWidth={12} strokeLinecap="round" opacity={0.45} filter="url(#soft)" />
      <line x1={190} y1={400} x2={190 + 520 * lineProgress} y2={400} stroke="url(#link)" strokeWidth={6} strokeLinecap="round" />
      <circle cx={pulseX} cy={400} r={11} fill="#FFFFFF" opacity={pulseOpacity * lineProgress} filter="url(#soft)" />
      <circle cx={pulseX} cy={400} r={7} fill="#FFFFFF" opacity={pulseOpacity * lineProgress} />
      <text x={450} y={452} textAnchor="middle" fontSize={30} fontWeight={800} fill={INK} opacity={lineLabel}>
        your tailnet
      </text>
    </svg>
  );
};

export const PrivateScene: React.FC<SceneProps> = () => {
  const {square, margin, height} = useLayout();
  const diagramWidth = square ? 780 : 900;
  const copy = (
    <Copy
      kicker="Your tailnet"
      lines={[
        {text: 'No relay.', at: local(0) + 8},
        {text: 'No account.', at: local(2)},
        {text: 'No backend.', at: local(4), accent: true},
      ]}
      sub="Point-to-point over your own Tailscale network."
      subAt={local(5) + 6}
      size={104}
    />
  );
  if (square) {
    return (
      <AbsoluteFill style={{fontFamily: SANS}}>
        <div style={{position: 'absolute', left: margin, right: margin, top: 70}}>{copy}</div>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 40, display: 'flex', justifyContent: 'center'}}>
          <PrivateDiagram width={diagramWidth} />
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{fontFamily: SANS, display: 'flex', flexDirection: 'row', alignItems: 'center', padding: `0 ${margin}px`}}>
      <div style={{flex: 1}}>{copy}</div>
      <div style={{width: diagramWidth + 40, display: 'flex', justifyContent: 'center', height}}>
        <div style={{alignSelf: 'center'}}>
          <PrivateDiagram width={diagramWidth} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const EndScene: React.FC<SceneProps> = () => {
  const {u, square} = useLayout();
  const frame = useCurrentFrame();
  const pill = reveal(frame, local(2), 30);
  return (
    <Centered>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center'}}>
        <AppIcon size={square ? 150 : 190} at={0} />
        <Rise at={10} style={{marginTop: 30 * u}}>
          <div style={{fontSize: 150 * u, fontWeight: 900, letterSpacing: '-0.05em', lineHeight: 1, color: INK}}>
            Tailscode
          </div>
        </Rise>
        <Rise at={local(1)} style={{marginTop: 26 * u}}>
          <div style={{fontSize: 70 * Math.max(u, 0.8), fontWeight: 800, letterSpacing: '-0.03em', color: INK}}>
            Free on the App Store.
          </div>
        </Rise>
        <Rise at={local(1) + 8} style={{marginTop: 10 * u}}>
          <div style={{fontSize: 38 * Math.max(u, 0.8), fontWeight: 500, color: DIM}}>
            Pro is a one-time $14.99. No subscription.
          </div>
        </Rise>
        <div
          style={{
            marginTop: 46 * u,
            padding: `${22 * Math.max(u, 0.8)}px ${54 * Math.max(u, 0.8)}px`,
            borderRadius: 999,
            background: BRAND_GRADIENT,
            opacity: pill,
            transform: `translateY(${(1 - pill) * 24}px) scale(${0.96 + 0.04 * pill})`,
            boxShadow: '0 20px 70px rgba(76,107,255,0.45)',
          }}
        >
          <div style={{fontSize: 62 * Math.max(u, 0.8), fontWeight: 800, letterSpacing: '-0.025em', color: '#FFFFFF'}}>
            midgarcorp.cc/tailscode
          </div>
        </div>
        <Rise at={local(3)} style={{marginTop: 40 * u}}>
          <div style={{fontSize: 32 * Math.max(u, 0.8), fontWeight: 500, color: FAINT, letterSpacing: '0.01em'}}>
            iPhone · iPad · Mac on the App Store   |   Linux on GitHub releases   |   GPL-3.0
          </div>
        </Rise>
      </div>
    </Centered>
  );
};
