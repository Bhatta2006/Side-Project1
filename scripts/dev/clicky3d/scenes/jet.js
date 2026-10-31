// Turbofan cutaway, built to match the HeyClicky reference: fan, compressor, combustor, turbine.
const SCENE = () => ({
  numbered: true,
  parts: [
    { id: 'engine', kind: 'group', at: [0, 1.1, 0] },
    { id: 'nacelle', parent: 'engine', kind: 'lathe', recipe: { profile: [[1.0, -2.05], [1.08, -1.75], [1.1, -1.2], [1.06, -0.2], [0.92, 0.7], [0.8, 1.25]], wall: 0.07, bevel: 0.02, axis: 'x', seg: 96 }, mat: 'alu', color: '#B8C2CE', cut: { normal: [0, 0.55, 1], offset: 0 } },
    { id: 'core', parent: 'engine', kind: 'lathe', recipe: { profile: [[0.56, -1.35], [0.6, -0.8], [0.62, 0.3], [0.52, 1.25], [0.42, 2.0]], wall: 0.04, axis: 'x', seg: 80 }, mat: 'steel', color: '#9AA3AE', cut: { normal: [0, 0.55, 1], offset: 0 } },
    { id: 'shaft', parent: 'engine', kind: 'cyl', recipe: { r: 0.075, h: 3.7, axis: 'x', bevel: 0.02 }, at: [0.15, 0, 0], mat: 'steel' },
    { id: 'fan', parent: 'engine', kind: 'rotor', recipe: { r: 0.97, hub: 0.26, blades: 22, chord: 0.36, pitch: 52, twist: 30, thick: 0.08, h: 0.32, spinner: 0.42, axis: '-x' }, at: [-1.62, 0, 0], mat: 'titanium', color: '#5E6672' },
    { id: 'compressor', parent: 'engine', kind: 'rotor', recipe: { r: 0.54, hub: 0.24, blades: 26, chord: 0.11, pitch: 38, twist: 14, thick: 0.08, h: 0.12, axis: 'x' }, at: [-1.18, 0, 0], copies: 6, step: [0.16, 0, 0], turn: [7, 0, 0], mat: 'steel', color: '#8D97A3' },
    { id: 'combustor', parent: 'engine', kind: 'tube', recipe: { r: 0.5, inner: 0.24, h: 0.62, axis: 'x', bevel: 0.03 }, at: [0.3, 0, 0], mat: 'copper', color: '#E8823A', cut: { normal: [0, 0.55, 1], offset: 0 } },
    { id: 'injector', parent: 'engine', kind: 'cyl', recipe: { r: 0.03, h: 0.18, axis: 'x' }, at: [-0.02, 0.37, 0], around: { axis: 'x', count: 12, center: [-0.02, 0, 0] }, mat: 'brass' },
    { id: 'turbine', parent: 'engine', kind: 'rotor', recipe: { r: 0.5, hub: 0.26, blades: 30, chord: 0.12, pitch: 30, twist: 10, thick: 0.12, h: 0.13, axis: 'x' }, at: [0.86, 0, 0], copies: 2, step: [0.18, 0, 0], mat: 'iron', color: '#7B6F66' },
    { id: 'cone', parent: 'engine', kind: 'lathe', recipe: { profile: [[0, 0.95], [0.12, 0.8], [0.25, 0.35], [0.27, 0]], axis: 'x' }, at: [1.25, 0, 0], mat: 'steel', color: '#A5ACB5' },
  ],
  labels: [
    { text: 'Fan', part: 'fan', anchor: [0, 0.62, 0], tone: 'pink' },
    { text: 'Compressor', part: 'compressor.3', anchor: [0, 0.4, 0], tone: 'green' },
    { text: 'Combustor', part: 'combustor', anchor: [0, 0.32, 0.18], tone: 'blue' },
    { text: 'Turbine', part: 'turbine.1', anchor: [0, 0.38, 0], tone: 'yellow' },
    { text: 'Exhaust', part: 'cone', anchor: [0.5, 0, 0], tone: 'violet' },
  ],
  camera: { yaw: -32, tilt: 18, distance: 1.05 },
});
