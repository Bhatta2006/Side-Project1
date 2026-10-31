// Every primitive kind on a grid, default-ish recipes, alternating materials.
const SCENE = () => {
  const kinds = [
    ['box', {size:[0.7,0.5,0.5]}], ['box', {size:[0.7,0.5,0.5], bevel:0.08}], ['cyl', {r:0.3,h:0.6}], ['cyl', {r:0.3,h:0.6,bevel:0.05}], ['cone', {r:0.32,h:0.6}],
    ['tube', {r:0.34,inner:0.24,h:0.5,bevel:0.02}], ['sphere', {r:0.32}], ['torus', {r:0.28,tube:0.08}], ['capsule', {r:0.18,h:0.6}], ['pipe', {points:[[-0.3,0,0],[0,0.3,0],[0.3,0,0.1]], r:0.06}],
    ['spring', {r:0.22,h:0.6,coils:5,wire:0.04}], ['gear', {r:0.32,w:0.14,teeth:14,hole:0.08}], ['extrude', {points:[[-0.3,-0.25],[0.3,-0.25],[0.3,0.05],[0,0.3],[-0.3,0.05]], depth:0.2, bevel:0.03, holes:[[0,-0.05,0.08]]}], ['blob', {balls:[[0,0,0,0.22],[0.2,0.12,0,0.16]], sticks:[[[0,0,0],[-0.2,0.3,0],0.06]]}], ['poly', {r:0.32, faces:20}],
    ['lathe', {profile:[[0.05,-0.3],[0.25,-0.3],[0.28,-0.1],[0.12,0.1],[0.1,0.3]], wall:0.03}], ['plate', {size:[0.7,0.05,0.5], holes:[[0.28,0.18,0.03],[-0.28,0.18,0.03]]}], ['rotor', {r:0.34, hub:0.1, blades:14, spinner:true}], ['airfoil', {chord:0.4, span:0.6}], ['loft', {sections:[[-0.35,0.1,0.1,2],[-0.2,0.4,0.3,3],[0.2,0.4,0.3,4],[0.35,0.2,0.15,2]]}],
    ['tire', {r:0.3, w:0.2, tread:20}], ['rim', {r:0.19, w:0.16, spokes:6}], ['arrow', {points:[[-0.3,0,0],[0.3,0.1,0]]}], ['surface', {grid:[[[-0.3,0,-0.3],[0,0.1,-0.3],[0.3,0,-0.3]],[[-0.3,0.1,0],[0,0.25,0],[0.3,0.1,0]],[[-0.3,0,0.3],[0,0.1,0.3],[0.3,0,0.3]]]}],
  ];
  const parts = kinds.map(([kind, recipe], i) => ({
    id: kind + i, kind, recipe: Object.assign({}, recipe, (kind==='tire'||kind==='rim') ? {axis:'x'} : {}),
    at: [(i % 5 - 2) * 0.95, 0.38, (Math.floor(i / 5) - 2) * 0.95],
    mat: kind === 'tire' ? 'rubber' : i % 2 ? 'alu' : 'plastic', color: i % 2 || kind === 'tire' ? undefined : '#E7C14A', double: kind === 'surface',
  }));
  return { parts, labels: [], camera: { yaw: -20, tilt: 34, distance: 0.95 } };
};
