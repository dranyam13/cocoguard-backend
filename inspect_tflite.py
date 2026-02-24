"""Inspect YOLO26s TFLite model output shape and run a dummy inference"""
import numpy as np
import os

MODEL_PATH = r'c:\xampp\htdocs\cocoguard\assets\model\best_float16.tflite'

try:
    import tensorflow as tf

    itp = tf.lite.Interpreter(model_path=MODEL_PATH)
    itp.allocate_tensors()

    inp_details = itp.get_input_details()
    out_details = itp.get_output_details()

    print("=" * 60)
    print("  YOLO26s TFLite TENSOR INSPECTION")
    print("=" * 60)
    print("\n--- INPUT TENSORS ---")
    for i, t in enumerate(inp_details):
        print(f"  [{i}] name  = {t['name']}")
        print(f"       shape = {t['shape']}  dtype={t['dtype'].__name__}")

    print("\n--- OUTPUT TENSORS ---")
    for i, t in enumerate(out_details):
        print(f"  [{i}] name  = {t['name']}")
        print(f"       shape = {t['shape']}  dtype={t['dtype'].__name__}")

    print(f"\n  Total output tensors : {len(out_details)}")

    # Run dummy inference with black image (zeros)
    print("\n--- DUMMY INFERENCE (black 512x512 image) ---")
    dummy = np.zeros(inp_details[0]['shape'], dtype=np.float32)
    itp.set_tensor(inp_details[0]['index'], dummy)
    itp.invoke()

    for i, t in enumerate(out_details):
        data = itp.get_tensor(t['index'])
        flat = data.flatten()
        nonzero = np.count_nonzero(flat)
        print(f"  output[{i}] shape={data.shape}  "
              f"min={flat.min():.4f}  max={flat.max():.4f}  "
              f"nonzero={nonzero}/{len(flat)}")
        if len(flat) <= 30:
            print(f"    values: {flat.tolist()}")

    print("\n  end2end=true means NMS is BAKED IN.")
    print("  If output shape is [1, N, 6] → each row is [x1,y1,x2,y2,conf,class_id]")
    print("  If multiple outputs → likely [boxes, scores, classes, num_detections]")
    print("=" * 60)

except ImportError:
    print("TensorFlow not installed in this env. Trying tflite-runtime...")
    try:
        import tflite_runtime.interpreter as tflite
        itp = tflite.Interpreter(model_path=MODEL_PATH)
        itp.allocate_tensors()
        inp_details = itp.get_input_details()
        out_details = itp.get_output_details()
        print("INPUT:", inp_details)
        print("OUTPUT:", out_details)
    except Exception as e2:
        print("FAILED:", e2)
except Exception as e:
    import traceback
    print("ERROR:", e)
    traceback.print_exc()
