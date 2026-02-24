"""Test YOLO26s end2end output with a real pest image or random noise"""
import numpy as np

MODEL_PATH = r'c:\xampp\htdocs\cocoguard\assets\model\best_float16.tflite'
LABELS = ['APW Adult', 'APW Larvae', 'Brontispa Adult', 'Brontispa Pupa',
          'Rhinoceros Beetle', 'Slug Caterpillar', 'White Grub']

import tensorflow as tf
itp = tf.lite.Interpreter(model_path=MODEL_PATH)
itp.allocate_tensors()
inp = itp.get_input_details()[0]
out = itp.get_output_details()[0]

print(f"Input  : {inp['shape']}  dtype={inp['dtype'].__name__}")
print(f"Output : {out['shape']}  dtype={out['dtype'].__name__}")
print()

# Test 1: random "noisy" image to see what spurious detections look like
np.random.seed(42)
noisy = np.random.rand(1, 512, 512, 3).astype(np.float32)
itp.set_tensor(inp['index'], noisy)
itp.invoke()
result = itp.get_tensor(out['index']).squeeze()  # [300, 6]

# Check columns
print("=== Column ranges [x1, y1, x2, y2, conf, class_id] ===")
for i, name in enumerate(['x1','y1','x2','y2','conf','class_id']):
    col = result[:, i]
    print(f"  col[{i}] {name:10s}: min={col.min():.4f}  max={col.max():.4f}  mean={col.mean():.4f}")

# Show highest-confidence detections
print("\n=== Top detections by confidence (noisy image) ===")
confs = result[:, 4]
top_idx = np.argsort(confs)[::-1][:10]
for idx in top_idx:
    x1, y1, x2, y2, conf, cls = result[idx]
    label = LABELS[int(round(cls))] if 0 <= int(round(cls)) < len(LABELS) else f'cls{cls:.0f}'
    print(f"  conf={conf:.4f}  class={int(round(cls))} ({label})  "
          f"box=[{x1:.1f},{y1:.1f},{x2:.1f},{y2:.1f}]")

# Determine if coords are pixel space or normalized
print(f"\n  Box x1/x2 max={result[:,0].max():.2f} / {result[:,2].max():.2f}")
print(f"  → Coords are {'PIXEL SPACE (0-512)' if result[:,2].max() > 2 else 'NORMALIZED (0-1)'}")
