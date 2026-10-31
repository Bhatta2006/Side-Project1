// Attachment test: only the body has coordinates; everything else is placed with `on`.
const SCENE = {
  parts: [
    { id: 'cam', kind: 'group', at: [0, 0, 0] },
    { id: 'body', parent: 'cam', kind: 'box', recipe: { size: [1.3, 0.9, 0.5], bevel: 0.08 }, at: [0, 0.45, 0], mat: 'black' },
    { id: 'grip', parent: 'cam', kind: 'box', recipe: { size: [0.32, 0.86, 0.28], bevel: 0.12 }, on: { part: 'body', face: '+z', align: [-0.78, 0, 0], inset: 0.3 }, mat: 'rubber' },
    { id: 'hump', parent: 'cam', kind: 'box', recipe: { size: [0.42, 0.24, 0.4], bevel: 0.06 }, on: { part: 'body', face: '+y', inset: 0.1 }, mat: 'black' },
    { id: 'dial', parent: 'cam', kind: 'gear', recipe: { r: 0.1, w: 0.06, teeth: 24, tooth: 0.015 }, rot: [90, 0, 0], on: { part: 'body', face: '+y', align: [0.62, 0, 0] }, mat: 'alu' },
    { id: 'button', parent: 'cam', kind: 'cyl', recipe: { r: 0.05, h: 0.05 }, on: { part: 'grip', face: '+y', align: [0, 0, 0.3] }, mat: 'chrome' },
    { id: 'screen', parent: 'cam', kind: 'box', recipe: { size: [0.8, 0.55, 0.04], bevel: 0.02 }, on: { part: 'body', face: '-z', align: [0.15, -0.1, 0] }, mat: 'glow', color: '#1E2A44', glow: 0.25 },
    { id: 'mount', parent: 'cam', kind: 'tube', recipe: { r: 0.3, inner: 0.24, h: 0.08, axis: 'z' }, on: { part: 'body', face: '+z', align: [0.12, -0.05, 0] }, mat: 'chrome' },
    { id: 'lens', parent: 'cam', kind: 'lathe', recipe: { profile: [[0.28, 0], [0.3, 0.1], [0.3, 0.5], [0.33, 0.62], [0.33, 0.8]], wall: 0.03, axis: 'z' }, on: { part: 'mount', face: '+z' }, mat: 'black' },
  ],
  labels: [{ text: 'Lens', part: 'lens', anchor: [0, 0.3, 0.4] }, { text: 'Screen', part: 'screen' }],
  camera: { yaw: -35, tilt: 18 },
};
