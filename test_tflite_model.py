"""Test TFLite model (YOLOv11-S Detect) to verify it produces valid output"""
import numpy as np
import os

# Try to import tensorflow
try:
    import tensorflow as tf
    print("Using TensorFlow Lite")
except ImportError:
    print("TensorFlow not found, trying tflite_runtime")
    import tflite_runtime.interpreter as tflite  # type: ignore[import-not-found]
    tf = None

# Load model - use the deployed model in cocoguard/assets/model
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cocoguard/assets/model/best_float16.tflite'))
print(f"Model path: {model_path}")
print(f"Model exists: {os.path.exists(model_path)}")
print(f"Model size: {os.path.getsize(model_path) / 1024 / 1024:.1f} MB")

if tf:
    interpreter = tf.lite.Interpreter(model_path=model_path)
else:
    interpreter = tflite.Interpreter(model_path=model_path)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print(f"\nInput shape: {input_details[0]['shape']}")
print(f"Input type: {input_details[0]['dtype']}")
print(f"Output shape: {output_details[0]['shape']}")
print(f"Output type: {output_details[0]['dtype']}")

LABELS = ['APW Adult', 'APW Larvae', 'Brontispa', 'Brontispa Pupa', 
          'Rhinoceros Beetle', 'Slug Caterpillar', 'White Grub']

# Test 1: Gray image (no pest - baseline)
print("\n=== TEST 1: Gray image (baseline) ===")
test_input = np.full((1, 640, 640, 3), 114.0/255.0, dtype=np.float32)
interpreter.set_tensor(input_details[0]['index'], test_input)
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])
print(f"Output shape: {output.shape}")
print(f"Output range: min={output.min():.6f}, max={output.max():.6f}")

output_sq = np.squeeze(output)  # [11, 8400]
class_logits = output_sq[4:11, :]  # 7 class logits (detect model: no mask coefficients)
class_probs = 1 / (1 + np.exp(-class_logits))
print(f"Class probs range: {class_probs.min():.4f} to {class_probs.max():.4f}")
print(f"Max prob: {class_probs.max()*100:.2f}%")

# Test 2: Try with a real image if available
print("\n=== TEST 2: Checking model output structure ===")
# Check first few values
print(f"Row 0 (cx) first 5: {output_sq[0, :5]}")
print(f"Row 1 (cy) first 5: {output_sq[1, :5]}")
print(f"Row 2 (w) first 5: {output_sq[2, :5]}")
print(f"Row 3 (h) first 5: {output_sq[3, :5]}")
print(f"Row 4 (class0) first 5 logits: {output_sq[4, :5]}")
print(f"Row 4 (class0) first 5 probs: {(1/(1+np.exp(-output_sq[4, :5])))*100}")

# Check what the output looks like when reshaped differently
# Maybe the Dart code reads the wrong layout
print(f"\nRow 4 last 5 logits: {output_sq[4, -5:]}")

# Count how many anchors have > 25% probs for each class
print("\n=== Detections at different thresholds (gray image) ===")
for thresh in [0.25, 0.50, 0.55]:
    max_probs = np.max(class_probs, axis=0)
    count = np.sum(max_probs >= thresh)
    print(f"  Threshold {thresh*100:.0f}%: {count} detections")

# Find scan files to test with
upload_dirs = [
    os.path.join(os.path.dirname(__file__), 'uploads/scans'),
    os.path.join(os.path.dirname(__file__), 'uploads/files'),
]
test_image = None
for d in upload_dirs:
    if os.path.exists(d):
        files = [f for f in os.listdir(d) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if files:
            test_image = os.path.join(d, files[0])
            break

if test_image:
    print(f"\n=== TEST 3: Real image: {os.path.basename(test_image)} ===")
    from PIL import Image
    img = Image.open(test_image).convert('RGB')
    print(f"Image size: {img.size}")
    
    # Letterbox preprocessing
    orig_w, orig_h = img.size
    scale = min(640/orig_w, 640/orig_h)
    new_w, new_h = int(orig_w*scale), int(orig_h*scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    letterbox = Image.new('RGB', (640, 640), (114, 114, 114))
    pad_x, pad_y = (640-new_w)//2, (640-new_h)//2
    letterbox.paste(resized, (pad_x, pad_y))
    
    img_array = np.array(letterbox, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    interpreter.set_tensor(input_details[0]['index'], img_array)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    
    output_sq = np.squeeze(output)
    class_logits = output_sq[4:11, :]
    class_probs = 1 / (1 + np.exp(-class_logits))
    
    print(f"Class probs range: {class_probs.min():.4f} to {class_probs.max():.4f}")
    print(f"Max prob: {class_probs.max()*100:.2f}%")
    
    max_probs = np.max(class_probs, axis=0)
    best_classes = np.argmax(class_probs, axis=0)
    
    for thresh in [0.25, 0.50, 0.55]:
        valid = max_probs >= thresh
        count = np.sum(valid)
        if count > 0:
            best_idx = np.argmax(max_probs)
            best_class = best_classes[best_idx]
            print(f"  Threshold {thresh*100:.0f}%: {count} detections, best: {LABELS[best_class]} at {max_probs[best_idx]*100:.1f}%")
        else:
            print(f"  Threshold {thresh*100:.0f}%: 0 detections")
else:
    print("\nNo test images found in uploads/")

print("\nDone!")
