
// Static content for the landing page.
// Metrics are from the final Exp2 Best YOLO11n model.
// Evaluation used a held-out test set containing two PCB boards.

export const MODEL_METRICS = [
  {
    label: 'Precision',
    value: '87.56%',
    hint: 'Macro average precision across the six defect classes',
  },
  {
    label: 'Recall',
    value: '96.83%',
    hint: 'Macro average recall across the six defect classes',
  },
  {
    label: 'mAP@50',
    value: '94.04%',
    hint: 'Mean average precision at IoU 0.50',
  },
  {
    label: 'mAP@50–95',
    value: '42.44%',
    hint: 'Mean average precision across IoU thresholds 0.50 to 0.95',
  },
]

export const METRICS_DISCLOSURE =
  'Results are from the final Exp2 Best YOLO11n model, evaluated on a held-out test set containing two PCB boards. ' +
  'Precision, recall and F1-related reporting use macro class averages. ' +
  'These are experimental results on a limited test set and do not guarantee performance on unseen PCB layouts or real-world production boards.'

export const DEFECT_CLASSES = [
  { key: 'mouse_bite', name: 'Mouse bite', icon: 'Scissors', text: 'Small, irregular notches bitten out of the board edge or a copper trace.' },
  { key: 'spur', name: 'Spur', icon: 'Spline', text: 'Unwanted copper spikes protruding from a trace.' },
  { key: 'missing_hole', name: 'Missing hole', icon: 'CircleDot', text: 'A drilled hole that should be present but is absent.' },
  { key: 'short', name: 'Short', icon: 'Zap', text: 'Unintended copper bridging between two conductors.' },
  { key: 'open_circuit', name: 'Open circuit', icon: 'Unplug', text: 'A break in a trace that interrupts the electrical path.' },
  { key: 'spurious_copper', name: 'Spurious copper', icon: 'Eraser', text: 'Leftover copper residue where none belongs.' },
]

export const STEPS = [
  { icon: 'ImagePlus', title: 'Provide an image', text: 'Upload a JPG, PNG or WEBP photo of a PCB (up to 10 MB), or capture one with your camera.' },
  { icon: 'ScanSearch', title: 'AI analysis', text: 'The image is sent to the FastAPI backend, where the fine-tuned YOLO11n model scans it once for the six supported defect types.' },
  { icon: 'FileText', title: 'Review and report', text: 'Compare the original and annotated images, inspect every detection, and download a PDF report. Results are saved to your history.' },
]

export const TECH_STACK = [
  { name: 'React 19', role: 'Interface' },
  { name: 'Vite', role: 'Build tooling' },
  { name: 'Tailwind CSS 4', role: 'Styling' },
  { name: 'FastAPI', role: 'REST API' },
  { name: 'Ultralytics YOLO11n', role: 'Detection model — Exp2 Best' },
  { name: 'SQLite', role: 'Inspection history' },
  { name: 'Pillow', role: 'Image validation' },
  { name: 'ReportLab', role: 'PDF reports' },
]
