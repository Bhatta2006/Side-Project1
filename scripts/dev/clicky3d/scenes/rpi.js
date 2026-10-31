// Raspberry Pi style board: PCB plate, SoC, RAM, GPIO header (2x20 array), USB/Ethernet blocks.
const SCENE = () => ({
  parts: [
    { id: 'board', kind: 'group', at: [0, 0.05, 0] },
    { id: 'pcb', parent: 'board', kind: 'plate', recipe: { size: [3.4, 0.06, 2.2], corner: 0.12, holes: [[-1.45, -0.85, 0.06], [1.05, -0.85, 0.06], [-1.45, 0.85, 0.06], [1.05, 0.85, 0.06]] }, mat: 'gloss', color: '#2F8F4E' },
    { id: 'soc', parent: 'board', kind: 'box', recipe: { size: [0.55, 0.08, 0.55], bevel: 0.015 }, at: [-0.35, 0.07, 0.05], mat: 'alu', color: '#C9CDD2' },
    { id: 'ram', parent: 'board', kind: 'box', recipe: { size: [0.5, 0.06, 0.42], bevel: 0.01 }, at: [0.45, 0.06, 0.05], mat: 'black' },
    { id: 'pmic', parent: 'board', kind: 'box', recipe: { size: [0.2, 0.04, 0.2], bevel: 0.006 }, at: [-0.95, 0.05, 0.45], mat: 'black', copies: 3, step: [0, 0, -0.38] },
    { id: 'gpio-base', parent: 'board', kind: 'box', recipe: { size: [2.05, 0.1, 0.2], bevel: 0.01 }, at: [-0.25, 0.08, -0.95], mat: 'black' },
    { id: 'pin', parent: 'board', kind: 'box', recipe: { size: [0.025, 0.24, 0.025] }, at: [-1.22, 0.2, -1.0], copies: 20, step: [0.102, 0, 0], mat: 'gold' },
    { id: 'pin2', parent: 'board', kind: 'box', recipe: { size: [0.025, 0.24, 0.025] }, at: [-1.22, 0.2, -0.9], copies: 20, step: [0.102, 0, 0], mat: 'gold' },
    { id: 'usb', parent: 'board', kind: 'box', recipe: { size: [0.62, 0.62, 0.5], bevel: 0.02 }, at: [1.45, 0.34, -0.45], copies: 2, step: [0, 0, 0.62], mat: 'chrome', color: '#C7CCD3' },
    { id: 'usb-tongue', parent: 'board', kind: 'box', recipe: { size: [0.05, 0.12, 0.34] }, at: [1.77, 0.34, -0.45], copies: 2, step: [0, 0, 0.62], mat: 'plastic', color: '#3F7BE8' },
    { id: 'eth', parent: 'board', kind: 'box', recipe: { size: [0.66, 0.56, 0.58], bevel: 0.02 }, at: [1.43, 0.31, 0.72], mat: 'chrome', color: '#C7CCD3' },
    { id: 'sd', parent: 'board', kind: 'box', recipe: { size: [0.42, 0.04, 0.46], bevel: 0.01 }, at: [-1.62, -0.03, 0.0], mat: 'black' },
    { id: 'cap', parent: 'board', kind: 'cyl', recipe: { r: 0.05, h: 0.12, bevel: 0.01 }, at: [-0.85, 0.09, -0.35], copies: 4, step: [0.14, 0, 0], mat: 'alu' },
  ],
  labels: [
    { text: 'USB ports', part: 'usb.0', anchor: [0, 0.31, 0], tone: 'blue' },
    { text: 'GPIO: electronics', part: 'pin', anchor: [0.8, 0.12, 0], tone: 'pink' },
    { text: 'Processor', part: 'soc', anchor: [0, 0.04, 0], tone: 'pink' },
    { text: 'RAM', part: 'ram', anchor: [0, 0.03, 0], tone: 'green' },
    { text: 'microSD storage', part: 'sd', anchor: [-0.1, 0, 0], tone: 'yellow' },
  ],
  camera: { yaw: -16, tilt: 34, distance: 1.0 },
});
