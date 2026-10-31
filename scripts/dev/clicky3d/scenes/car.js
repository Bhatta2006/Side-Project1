// Toy roadster: lofted body, cabin, seats, windshield, four wheels (tyre + rim).
const SCENE = () => {
  const wheel = (id, x, z) => [
    { id: id + '-tyre', parent: 'car', kind: 'tire', recipe: { r: 0.42, w: 0.3, inner: 0.27, tread: 0, axis: 'x' }, at: [x, 0.42, z], mat: 'rubber' },
    { id: id + '-rim', parent: 'car', kind: 'rim', recipe: { r: 0.27, w: 0.24, spokes: 10, spokeWidth: 0.03, axis: x > 0 ? 'x' : '-x' }, at: [x, 0.42, z], mat: 'paint', color: '#6F9DB3' },
  ];
  return {
    parts: [
      { id: 'car', kind: 'group', at: [0, 0, 0] },
      { id: 'body', parent: 'car', kind: 'loft', recipe: { sections: [[-1.75, 1.3, 0.42, 5, 0.62], [-1.5, 1.55, 0.62, 6, 0.66], [-0.6, 1.62, 0.66, 7, 0.66], [0.6, 1.62, 0.62, 7, 0.64], [1.55, 1.55, 0.6, 6, 0.64], [1.82, 1.25, 0.4, 5, 0.62]], smooth: 4 }, mat: 'gloss', color: '#E2B73A' },
      { id: 'sill', parent: 'car', kind: 'box', recipe: { size: [1.7, 0.16, 3.0], bevel: 0.07 }, at: [0, 0.34, 0], mat: 'black' },
      { id: 'fender', parent: 'car', kind: 'torus', recipe: { r: 0.5, tube: 0.12, arc: 150, start: -75 }, rot: [0, 0, 90], at: [0.78, 0.45, 1.15], copies: 2, step: [-1.56, 0, 0], mat: 'gloss', color: '#E2B73A' },
      { id: 'fender-r', parent: 'car', kind: 'torus', recipe: { r: 0.5, tube: 0.12, arc: 150, start: -75 }, rot: [0, 0, 90], at: [0.78, 0.45, -1.15], copies: 2, step: [-1.56, 0, 0], mat: 'gloss', color: '#E2B73A' },
      { id: 'seat', parent: 'car', kind: 'box', recipe: { size: [0.46, 0.62, 0.18], bevel: 0.08 }, at: [0.34, 1.12, -0.25], rot: [-12, 0, 0], copies: 2, step: [-0.68, 0, 0], mat: 'soft', color: '#2E3036' },
      { id: 'frame', parent: 'car', kind: 'pipe', recipe: { points: [[-0.72, 0, 0], [-0.68, 0.48, -0.08], [0.68, 0.48, -0.08], [0.72, 0, 0]], r: 0.035, smooth: false }, at: [0, 0.98, 0.42], mat: 'black' },
      { id: 'glass', parent: 'car', kind: 'box', recipe: { size: [1.3, 0.42, 0.03], bevel: 0.01 }, at: [0, 1.24, 0.4], rot: [-14, 0, 0], mat: 'glass', opacity: 0.35 },
      { id: 'lamp', parent: 'car', kind: 'capsule', recipe: { r: 0.08, h: 0.12, axis: 'z' }, at: [0.56, 0.86, 1.78], copies: 2, step: [-1.12, 0, 0], mat: 'ceramic', color: '#F4F1EA' },
      { id: 'grille', parent: 'car', kind: 'box', recipe: { size: [0.04, 0.28, 0.04] }, at: [-0.24, 0.66, 1.83], copies: 7, step: [0.08, 0, 0], mat: 'chrome' },
    ].concat(wheel('fl', 0.82, 1.15), wheel('fr', -0.82, 1.15), wheel('rl', 0.82, -1.15), wheel('rr', -0.82, -1.15)),
    labels: [],
    camera: { yaw: -52, tilt: 14, distance: 1.0 },
  };
};
