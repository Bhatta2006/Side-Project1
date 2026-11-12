export type PaperTileName = 'relief' | 'slip' | 'fibre' | 'cloud' | 'mottle' | 'linen' | 'kraft'

export interface PaperTile {
  uri: string
  width: number
  height: number
  cssWidth: number
  cssHeight: number
  bytes: number
  alpha: number
  shift: number
}

export const PAPER_RELIEF: PaperTile = {
  uri: '/ink/tiles/paper-relief.png',
  width: 384,
  height: 384,
  cssWidth: 192,
  cssHeight: 192,
  bytes: 36371,
  alpha: 12.2,
  shift: -2.78,
}

export const PAPER_SLIP: PaperTile = {
  uri: '/ink/tiles/paper-slip.png',
  width: 256,
  height: 256,
  cssWidth: 128,
  cssHeight: 128,
  bytes: 20322,
  alpha: 12.6,
  shift: -2.64,
}

export const PAPER_FIBRE: PaperTile = {
  uri: '/ink/tiles/paper-fibre.png',
  width: 480,
  height: 480,
  cssWidth: 240,
  cssHeight: 240,
  bytes: 3525,
  alpha: 0.4,
  shift: -0.05,
}

export const PAPER_CLOUD: PaperTile = {
  uri: '/ink/tiles/paper-cloud.png',
  width: 240,
  height: 240,
  cssWidth: 720,
  cssHeight: 720,
  bytes: 11669,
  alpha: 3.2,
  shift: -0.81,
}

export const PAPER_MOTTLE: PaperTile = {
  uri: '/ink/tiles/paper-mottle.png',
  width: 180,
  height: 180,
  cssWidth: 720,
  cssHeight: 720,
  bytes: 6737,
  alpha: 7.3,
  shift: -2.90,
}

export const PAPER_LINEN: PaperTile = {
  uri: '/ink/tiles/paper-linen.png',
  width: 320,
  height: 320,
  cssWidth: 160,
  cssHeight: 160,
  bytes: 34384,
  alpha: 7.4,
  shift: -1.58,
}

export const PAPER_KRAFT: PaperTile = {
  uri: '/ink/tiles/paper-kraft.png',
  width: 384,
  height: 192,
  cssWidth: 192,
  cssHeight: 96,
  bytes: 20826,
  alpha: 21.8,
  shift: -5.22,
}

export const PAPER_TILES: Record<PaperTileName, PaperTile> = {
  relief: PAPER_RELIEF,
  slip: PAPER_SLIP,
  fibre: PAPER_FIBRE,
  cloud: PAPER_CLOUD,
  mottle: PAPER_MOTTLE,
  linen: PAPER_LINEN,
  kraft: PAPER_KRAFT,
}
