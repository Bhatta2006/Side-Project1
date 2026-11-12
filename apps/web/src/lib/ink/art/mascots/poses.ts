import { defineMascot } from '@/lib/ink/art/types'
import { pose } from '@/lib/ink/art/mascots/body'
import {
  arrow, cableCut, celebrateDef, dashedFrame, magnifier, parcel, questions, stopSign, sweatDrop, thoughtCloud, waveDef, writeDef, zzz,
} from '@/lib/ink/art/mascots/props'

export const poses = defineMascot({
  idle: pose({ face: { eyes: 'dot', mouth: 'smile' }, tags: ['default', 'stand', 'hello'] }),
  wave: waveDef(0),
  think: pose({ face: { eyes: 'dot', look: [-1.4, -1.2], mouth: 'flat', brows: 'one' }, turn: { rot: -5 }, acc: thoughtCloud, tags: ['thinking', 'hmm', 'idea', 'ponder'] }),
  write: writeDef(2),
  sketch: pose({ face: { eyes: 'wink', mouth: 'smile' }, turn: { rot: 6, dx: -4 }, acc: dashedFrame, tags: ['draw', 'placeholder', 'measure', 'plan'] }),
  celebrate: celebrateDef(0),
  oops: pose({ face: { eyes: 'wide', mouth: 'wavy', blush: false }, turn: { rot: 7 }, tip: 'snapped', acc: sweatDrop, tags: ['error', 'sorry', 'broke', 'uh oh'] }),
  shrug: pose({ face: { eyes: 'dot', mouth: 'wavy', brows: 'shrug' }, turn: { rot: -5, sx: 1.02, sy: 0.97 }, acc: questions, tags: ['not found', 'unsure', 'dunno', 'lost'] }),
  sleep: pose({ face: { eyes: 'closed', mouth: 'yawn' }, turn: { rot: -10 }, acc: zzz, tags: ['quiet', 'idle', 'nap', 'zzz'] }),
  peek: pose({ face: { eyes: 'dot', look: [2, 0], mouth: 'smile' }, peek: true, tags: ['hide', 'edge', 'coming soon', 'curious'] }),
  point: pose({ face: { eyes: 'dot', look: [1.8, -0.4], mouth: 'smile' }, turn: { rot: 3, dx: -5 }, acc: arrow, tags: ['look', 'here', 'tour', 'hint'] }),
  carry: pose({ face: { eyes: 'squint', mouth: 'o' }, turn: { rot: -4, dx: -5 }, acc: parcel, tags: ['upload', 'file', 'move', 'heavy'] }),
  halt: pose({ face: { eyes: 'dot', mouth: 'flat', brows: 'worry' }, turn: { rot: -3 }, acc: stopSign, tags: ['stop', 'denied', 'forbidden', 'locked'] }),
  search: pose({ face: { eyes: 'lens', mouth: 'o' }, turn: { rot: -3 }, acc: magnifier, tags: ['find', 'look', 'zoom', 'no results'] }),
  unplug: pose({ face: { eyes: 'dot', look: [0.8, 1.6], mouth: 'frown', brows: 'worry' }, turn: { rot: -4, sy: 0.96 }, acc: cableCut, tags: ['offline', 'disconnected', 'network', 'cable'] }),
})
