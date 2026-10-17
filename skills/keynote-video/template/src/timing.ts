export const FPS = 30;
export const TOTAL = 900;
export const OVERLAP = 14;
export const BEAT_SECONDS = 0.85742;
export const FIRST_BEAT = 0.632;

export const beatFrame = (k: number): number => Math.round((FIRST_BEAT + BEAT_SECONDS * k) * FPS);

export const local = (beats: number): number => Math.round(beats * BEAT_SECONDS * FPS);

export type SceneId = 'open' | 'title' | 'device' | 'end';

const STARTS: [SceneId, number][] = [
  ['open', 0],
  ['title', beatFrame(4)],
  ['device', beatFrame(9)],
  ['end', beatFrame(28)],
];

export interface SceneSpan {
  id: SceneId;
  from: number;
  len: number;
  last: boolean;
}

export const SPANS: SceneSpan[] = STARTS.map(([id, from], i) => {
  const next = i + 1 < STARTS.length ? STARTS[i + 1][1] : TOTAL;
  return {id, from, len: next - from, last: i + 1 === STARTS.length};
});
