import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {useVideoConfig} from 'remotion';

export const SANS = loadInter('normal', {weights: ['500', '700', '800', '900'], subsets: ['latin']}).fontFamily;

export const BG = '#06070B';
export const INK = '#F5F6F8';
export const DIM = 'rgba(245,246,248,0.62)';
export const FAINT = 'rgba(245,246,248,0.34)';
export const ACCENT = '#4C8DFF';
export const BRAND_GRADIENT = 'linear-gradient(120deg, #7DB4FF 0%, #4C6BFF 48%, #9B6BFF 100%)';

export interface Layout {
  square: boolean;
  u: number;
  width: number;
  height: number;
  margin: number;
}

export const useLayout = (): Layout => {
  const {width, height} = useVideoConfig();
  const square = width === height;
  return {square, u: square ? 0.62 : 1, width, height, margin: square ? 72 : 120};
};
