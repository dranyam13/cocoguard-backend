"""
Pest Detection Prediction Service
Uses YOLO26s Detect TFLite model for coconut pest detection.
Input size: 512x512 | Output format: [1, 300, 6] — end2end, NMS baked in
Each detection row: [x1, y1, x2, y2, conf, class_id] — all normalized [0, 1]
Labels (0-6): APW Adult, APW Larvae, Brontispa Adult, Brontispa Pupa,
              Rhinoceros Beetle, Slug Caterpillar, White Grub
"""

import os
import numpy as np
from PIL import Image
from typing import List, Dict, Tuple, Optional
import io


class PestPredictionService:
    """Service for pest detection using TFLite model"""
    
    def __init__(self):
        self.model = None
        self.labels = []
        self.input_details = None
        self.output_details = None
        self.model_loaded = False
        
        # Default paths - can be overridden
        self.model_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../../cocoguard/assets/model/best_float16.tflite')
        )
        self.labels_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../../cocoguard/assets/model/labels.txt')
        )
        
    def load_model(self) -> bool:
        """Load the TFLite model and labels"""
        try:
            import tensorflow as tf
            
            # Load TFLite model
            if not os.path.exists(self.model_path):
                print(f"[ERROR] Model file not found: {self.model_path}")
                return False
                
            self.model = tf.lite.Interpreter(model_path=self.model_path)
            self.model.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.model.get_input_details()
            self.output_details = self.model.get_output_details()
            
            print(f"[INFO] Model loaded successfully from {self.model_path}")
            print(f"[INFO] Input shape: {self.input_details[0]['shape']}")
            print(f"[INFO] Output shape: {self.output_details[0]['shape']}")
            
            # Load labels
            if not os.path.exists(self.labels_path):
                print(f"[ERROR] Labels file not found: {self.labels_path}")
                return False
                
            with open(self.labels_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines() if line.strip()]
            
            print(f"[INFO] Loaded {len(self.labels)} labels: {self.labels}")
            
            self.model_loaded = True
            self._validate_yolo26s_constants()
            return True
            
        except ImportError:
            print("[ERROR] TensorFlow not installed. Please install with: pip install tensorflow")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load model: {str(e)}")
            return False
    
    def _validate_yolo26s_constants(self):
        """
        Startup sanity check — confirms YOLO26s end2end model constants match expectations.
        Expected input:  [1, 512, 512, 3]
        Expected output: [1, 300, 6]  (300 post-NMS detections, 6 values each)
        Prints a clear PASS/FAIL summary on first model load.
        """
        EXPECTED_INPUT  = (1, 512, 512, 3)
        EXPECTED_OUTPUT = (1, 300, 6)
        EXPECTED_LABELS = 7

        input_shape  = tuple(self.input_details[0]['shape'].tolist())
        output_shape = tuple(self.output_details[0]['shape'].tolist())
        num_labels   = len(self.labels)

        ok_input  = input_shape  == EXPECTED_INPUT
        ok_output = output_shape == EXPECTED_OUTPUT
        ok_labels = num_labels   == EXPECTED_LABELS

        print("\n" + "=" * 55)
        print("  YOLO26s STARTUP VALIDATION")
        print("=" * 55)
        print(f"  input  shape  : {input_shape}  {'✅' if ok_input  else '❌ expected (1,512,512,3)'}")
        print(f"  output shape  : {output_shape}  {'✅' if ok_output else '❌ expected (1,300,6)'}")
        print(f"  labels count  : {num_labels}  {'✅' if ok_labels else '❌ expected 7'}")
        print(f"  labels[0-6]   : {self.labels}")
        all_ok = ok_input and ok_output and ok_labels
        status = "✅  ALL CHECKS PASSED — YOLO26s ready" if all_ok else "⚠️  SOME CHECKS FAILED — review above"
        print(f"  {status}")
        print("=" * 55 + "\n")

    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """
        Preprocess image for YOLO model inference.
        Uses letterbox resizing to maintain aspect ratio (matches training preprocessing).
        """
        # Get expected input size from model
        input_shape = self.input_details[0]['shape']
        target_h, target_w = input_shape[1], input_shape[2]  # 512x512 for YOLO26s
        
        # Convert to RGB
        image = image.convert('RGB')
        orig_w, orig_h = image.size
        
        # Calculate letterbox scaling (maintain aspect ratio)
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        # Resize with high-quality resampling
        resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create letterbox canvas (gray padding, standard YOLO)
        letterbox = Image.new('RGB', (target_w, target_h), (114, 114, 114))
        
        # Paste resized image centered
        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2
        letterbox.paste(resized, (pad_x, pad_y))
        
        # Convert to numpy array and normalize to [0, 1]
        img_array = np.array(letterbox, dtype=np.float32) / 255.0
        
        # Add batch dimension: [H, W, C] -> [1, H, W, C]
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
    
    def predict(self, image: Image.Image, confidence_threshold: float = 0.70) -> Dict:
        """
        Run prediction on an image
        
        Args:
            image: PIL Image object
            confidence_threshold: Minimum confidence to report detection
            
        Returns:
            Dictionary with prediction results
        """
        if not self.model_loaded:
            if not self.load_model():
                return {
                    "success": False,
                    "error": "Model not loaded",
                    "predictions": []
                }
        
        try:
            # Preprocess image
            input_data = self.preprocess_image(image)
            
            # Run inference
            self.model.set_tensor(self.input_details[0]['index'], input_data)
            self.model.invoke()
            
            # Get output
            output_data = self.model.get_tensor(self.output_details[0]['index'])
            
            # Process YOLO output
            predictions = self._process_yolo_output(output_data, confidence_threshold)
            
            return {
                "success": True,
                "predictions": predictions,
                "total_detections": len(predictions)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "predictions": []
            }
    
    def _process_yolo_output(self, output: np.ndarray, threshold: float) -> List[Dict]:
        """
        Process YOLO26s end2end TFLite output: [1, 300, 6]
        NMS is baked into the model — no anchor decomposition or sigmoid needed.
        Each row: [x1, y1, x2, y2, conf, class_id] — all values normalized [0, 1].

        conf baseline for non-pest images: max ≈ 0.0013 (0.13%).
        conf for real pest detections:  typically 30–95%.
        Safe threshold: 0.25 (25%).
        """
        LABELS = [
            'APW Adult',         # 0
            'APW Larvae',        # 1
            'Brontispa Adult',   # 2
            'Brontispa Pupa',    # 3
            'Rhinoceros Beetle', # 4
            'Slug Caterpillar',  # 5
            'White Grub',        # 6
        ]
        NUM_CLASSES    = 7
        APW_LARVAE_ID  = 1
        WHITE_GRUB_ID  = 6
        BRONTISPA_ID   = 2
        BRONTISPA_PUPA_ID = 3
        RHINO_ID       = 4

        # Class-specific minimum confidences - ONLY for genuine pest validation
        # Morphological guards (size/shape) handle non-pest rejection separately
        CLASS_MIN_CONF = {
            0: 0.68,  # APW Adult
            1: 0.78,  # APW Larvae (keep high due to low samples)
            2: 0.68,  # Brontispa Adult
            3: 0.68,  # Brontispa Pupa
            4: 0.68,  # Rhinoceros Beetle — lowered, morphology guards do the filtering
            5: 0.68,  # Slug Caterpillar
            6: 0.70,  # White Grub
        }

        try:
            # Remove batch dimension: [1, 300, 6] → [300, 6]
            output = np.squeeze(output)
            if output.ndim != 2 or output.shape[1] != 6:
                print(f"[ERROR] Unexpected output shape after squeeze: {output.shape}")
                return []

            num_rows = output.shape[0]
            print(f"[DEBUG] end2end output: {num_rows} detection slots (post-NMS)")

            # Count raw per-class slots for APW/WG domain rule (any non-noise mention)
            raw_class_counts: Dict[int, int] = {i: 0 for i in range(NUM_CLASSES)}
            for row in output:
                raw_conf = float(row[4])
                raw_cls  = int(round(float(row[5])))
                if 0 <= raw_cls < NUM_CLASSES and raw_conf > 0.01:
                    raw_class_counts[raw_cls] += 1

            # Keep best detection per class above threshold
            best_per_class: Dict[int, Dict] = {}
            for row in output:
                x1, y1, x2, y2, conf, cls_f = row
                conf = float(conf)
                if conf < threshold:
                    continue
                cls = int(round(float(cls_f)))
                if cls < 0 or cls >= NUM_CLASSES:
                    continue
                if cls not in best_per_class or conf > best_per_class[cls]['_conf']:
                    best_per_class[cls] = {
                        '_conf':      conf,
                        'pest_type':  LABELS[cls],
                        'confidence': round(conf * 100, 2),
                        'class_id':   cls,
                        'bbox': {
                            'x':      round(float((x1 + x2) / 2), 4),
                            'y':      round(float((y1 + y2) / 2), 4),
                            'width':  round(float(x2 - x1), 4),
                            'height': round(float(y2 - y1), 4),
                        },
                    }

            predictions = sorted(best_per_class.values(), key=lambda p: -p['_conf'])

            print(f"\n=== DETECTION RESULTS (threshold={threshold*100:.0f}%) ===")
            for p in predictions:
                print(f"  {p['pest_type']}: {p['confidence']}%")
            print("=" * 50)

            if not predictions:
                return []

            # ╔════════════════════════════════════════════════════════════════╗
            # ║  MORPHOLOGY-FIRST FILTERING: Check size/shape BEFORE confidence ║
            # ║  Rejects ants/spiders based on physical characteristics        ║
            # ╚════════════════════════════════════════════════════════════════╝
            
            top_cls = predictions[0]['class_id']
            bbox = predictions[0].get('bbox') or {}
            width = float(bbox.get('width', 0.0))
            height = float(bbox.get('height', 0.0))
            area = width * height
            aspect_ratio = max(width, height) / max(min(width, height), 0.001)
            
            print(f"[DEBUG] Bbox analysis: area={area:.4f}, aspect_ratio={aspect_ratio:.2f}")
            
            # Rhinoceros Beetle morphology guards
            if top_cls == RHINO_ID:
                # Real Rhinoceros Beetles are LARGE (area > 0.15) and COMPACT (aspect < 2.0)
                # Ants are tiny, spiders are elongated
                if area < 0.15:
                    print(f"[DEBUG] ❌ Rhino bbox too small (area={area:.4f} < 0.15) → ANT/INSECT detected, rejecting")
                    return []
                if aspect_ratio > 2.0:
                    print(f"[DEBUG] ❌ Rhino aspect ratio elongated ({aspect_ratio:.2f} > 2.0) → SPIDER detected, rejecting")
                    return []
                print(f"[DEBUG] ✅ Rhino morphology check passed (large beetle-shaped object)")

            # Brontispa morphology guards
            if top_cls in [BRONTISPA_ID, BRONTISPA_PUPA_ID]:
                # Brontispa are medium-sized beetles, not spider-like
                if aspect_ratio > 1.8:
                    print(f"[DEBUG] ❌ Brontispa aspect ratio elongated ({aspect_ratio:.2f} > 1.8) → SPIDER detected, rejecting")
                    return []
                if area < 0.10:
                    print(f"[DEBUG] ❌ Brontispa bbox too small (area={area:.4f} < 0.10) → INSECT detected, rejecting")
                    return []
                print(f"[DEBUG] ✅ Brontispa morphology check passed")

            # Additional guards for non-pest objects:
            # - Require high top confidence
            # - Require sufficient gap to the next class
            top_conf = predictions[0]['_conf']
            second_conf = predictions[1]['_conf'] if len(predictions) > 1 else 0.0
            gap = top_conf - second_conf

            # If overall confidence is low or the gap is small, treat as non-pest noise
            if top_conf < 0.68:
                print(f"[DEBUG] ❌ Top confidence {top_conf*100:.1f}% < 68% → non-pest")
                return []
            if gap < 0.18 and top_conf < 0.80:
                print(f"[DEBUG] ❌ Gap {gap*100:.1f}% too small with conf {top_conf*100:.1f}% → non-pest")
                return []

            # Class-specific minimum confidence check (after morphology passes)
            cls_min = CLASS_MIN_CONF.get(top_cls, 0.70)
            if top_conf < cls_min:
                print(f"[DEBUG] ❌ {predictions[0]['pest_type']} below class min {cls_min*100:.0f}% → non-pest")
                return []

            # Domain Rule 1: multi-class confusion guard
            # Allow: APW Larvae + White Grub pair, or Brontispa life-stage pair.
            if len(predictions) >= 2:
                class_ids = {p['class_id'] for p in predictions}
                is_apw_wg    = class_ids == {APW_LARVAE_ID, WHITE_GRUB_ID}
                is_brontispa = class_ids == {BRONTISPA_ID, BRONTISPA_PUPA_ID}
                if not is_apw_wg and not is_brontispa:
                    names = [p['pest_type'] for p in predictions]
                    print(f"[DEBUG] ⚠️ Multi-class confusion ({', '.join(names)}) — likely non-pest image")
                    return []

            # Domain Rule 2: APW Larvae always beats White Grub
            has_apw = any(p['class_id'] == APW_LARVAE_ID for p in predictions)
            has_wg  = any(p['class_id'] == WHITE_GRUB_ID  for p in predictions)

            if has_wg:
                if has_apw:
                    apw_pred = next(p for p in predictions if p['class_id'] == APW_LARVAE_ID)
                    wg_pred  = next(p for p in predictions if p['class_id'] == WHITE_GRUB_ID)
                    if wg_pred['_conf'] > apw_pred['_conf']:
                        apw_pred['_conf']      = wg_pred['_conf']
                        apw_pred['confidence'] = wg_pred['confidence']
                    predictions = [p for p in predictions if p['class_id'] != WHITE_GRUB_ID]
                    print("[DEBUG] ✅ Both APW Larvae + White Grub — kept APW Larvae, removed WG")
                elif raw_class_counts.get(APW_LARVAE_ID, 0) >= 1:
                    wg_pred = next(p for p in predictions if p['class_id'] == WHITE_GRUB_ID)
                    raw_apw = raw_class_counts[APW_LARVAE_ID]
                    print(f"[DEBUG] ⚠️ White Grub + {raw_apw} raw APW Larvae slots → reclassifying as APW Larvae")
                    wg_pred['pest_type'] = LABELS[APW_LARVAE_ID]
                    wg_pred['class_id']  = APW_LARVAE_ID
                    print("[DEBUG] ✅ Reclassified: White Grub → APW Larvae")

            # Domain Rule 3: Brontispa life-stage disambiguation — keep higher confidence
            has_brontispa      = any(p['class_id'] == BRONTISPA_ID      for p in predictions)
            has_brontispa_pupa = any(p['class_id'] == BRONTISPA_PUPA_ID for p in predictions)

            if has_brontispa and has_brontispa_pupa:
                b_pred   = next(p for p in predictions if p['class_id'] == BRONTISPA_ID)
                pupa_pred = next(p for p in predictions if p['class_id'] == BRONTISPA_PUPA_ID)
                if pupa_pred['_conf'] >= b_pred['_conf']:
                    predictions = [p for p in predictions if p['class_id'] != BRONTISPA_ID]
                    print(f"[DEBUG] Brontispa both detected — kept Brontispa Pupa ({pupa_pred['confidence']}%)")
                else:
                    predictions = [p for p in predictions if p['class_id'] != BRONTISPA_PUPA_ID]
                    print(f"[DEBUG] Brontispa both detected — kept Brontispa Adult ({b_pred['confidence']}%)")

            # Strip internal key before returning
            for p in predictions:
                p.pop('_conf', None)

            predictions.sort(key=lambda p: p['confidence'], reverse=True)
            print(f"[DEBUG] Returning {len(predictions)} prediction(s)")
            return predictions

        except Exception as e:
            print(f"[ERROR] Failed to process YOLO end2end output: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def predict_from_bytes(self, image_bytes: bytes, confidence_threshold: float = 0.5) -> Dict:
        """Run prediction from image bytes"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return self.predict(image, confidence_threshold)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load image: {str(e)}",
                "predictions": []
            }
    
    def predict_from_path(self, image_path: str, confidence_threshold: float = 0.5) -> Dict:
        """Run prediction from image file path"""
        try:
            image = Image.open(image_path)
            return self.predict(image, confidence_threshold)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load image: {str(e)}",
                "predictions": []
            }
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "labels_path": self.labels_path,
            "labels": self.labels,
            "num_classes": len(self.labels),
            "input_shape": self.input_details[0]['shape'].tolist() if self.input_details else None,
            "output_shape": self.output_details[0]['shape'].tolist() if self.output_details else None
        }


# Singleton instance
_prediction_service: Optional[PestPredictionService] = None


def get_prediction_service() -> PestPredictionService:
    """Get or create the prediction service singleton"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PestPredictionService()
        _prediction_service.load_model()
    return _prediction_service
