import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {fadeOut, reveal} from './anim';
import {Backdrop} from './parts';
import {BG} from './theme';
import {DeviceScene, EndScene, OpenScene, TitleScene} from './scenes';
import {OVERLAP, SPANS, SceneId} from './timing';

const SCENES: Record<SceneId, React.FC<{len: number}>> = {
  open: OpenScene,
  title: TitleScene,
  device: DeviceScene,
  end: EndScene,
};

const Crossfade: React.FC<{len: number; first: boolean; last: boolean; children: React.ReactNode}> = ({
  len,
  first,
  last,
  children,
}) => {
  const frame = useCurrentFrame();
  const intro = first ? 1 : reveal(frame, 0, OVERLAP);
  const outro = last ? 1 : fadeOut(frame, len, OVERLAP);
  return <AbsoluteFill style={{opacity: Math.min(intro, outro)}}>{children}</AbsoluteFill>;
};

export const Launch: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: BG}}>
    <Backdrop />
    {SPANS.map((span, index) => {
      const Scene = SCENES[span.id];
      return (
        <Sequence
          key={span.id}
          from={span.from}
          durationInFrames={span.len + (span.last ? 0 : OVERLAP)}
          name={span.id}
        >
          <Crossfade len={span.len} first={index === 0} last={span.last}>
            <Scene len={span.len} />
          </Crossfade>
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
