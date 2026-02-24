"""
Surgically rewrite offline_prediction_service.dart for YOLO26s end2end format.
- Removes _sigmoid() and _processYoloOutput() (~370 lines)
- Inserts _processEnd2EndOutput() (~80 lines)
- Replaces the predict() output-reading section
- Simplifies predict() post-filter section
"""

DART_FILE = r'c:\xampp\htdocs\cocoguard\lib\services\offline_prediction_service.dart'

NEW_PROCESS_METHOD = '''
  /// Parse YOLO26s end2end TFLite output — flat [300 * 6] float array.
  ///
  /// Each of the 300 rows: [x1, y1, x2, y2, conf, class_id]
  ///   - x1,y1,x2,y2  : normalized [0, 1] in input image space
  ///   - conf          : final confidence [0, 1] (NMS already applied by model)
  ///   - class_id      : float 0.0–6.0 (round to nearest integer)
  ///
  /// Strategy:
  ///   1. Filter detections below confidence threshold.
  ///   2. Keep best (highest-conf) box per class.
  ///   3. Apply domain disambiguation rules (APW/WG, Brontispa/Pupa).
  List<Map<String, dynamic>> _processEnd2EndOutput(
    Float32List raw,
    double threshold,
  ) {
    const int numCols = 6; // [x1, y1, x2, y2, conf, class_id]
    final bestPerClass = <int, Map<String, dynamic>>{};

    for (int d = 0; d < maxDetections; d++) {
      final base = d * numCols;
      final conf = raw[base + 4];
      if (conf < threshold) continue;

      final classId = raw[base + 5].round().clamp(0, numClasses - 1);
      final prevBest = bestPerClass[classId];
      if (prevBest != null && (prevBest['_conf'] as double) >= conf) continue;

      final x1 = raw[base + 0].clamp(0.0, 1.0);
      final y1 = raw[base + 1].clamp(0.0, 1.0);
      final x2 = raw[base + 2].clamp(0.0, 1.0);
      final y2 = raw[base + 3].clamp(0.0, 1.0);
      final label =
          classId < _labels.length ? _labels[classId] : 'Unknown($classId)';

      bestPerClass[classId] = {
        '_conf': conf,
        'pest_type': label,
        'confidence': (conf * 100).roundToDouble(),
        'class_id': classId,
        'bbox': {
          'x': (x1 + x2) / 2,
          'y': (y1 + y2) / 2,
          'width': x2 - x1,
          'height': y2 - y1,
        },
      };
    }

    final predictions = bestPerClass.values.toList()
      ..sort(
        (a, b) =>
            (b['confidence'] as double).compareTo(a['confidence'] as double),
      );

    for (final p in predictions) {
      debugPrint(
        '🤖 [TFLite] Candidate: ${p['pest_type']} @ ${p['confidence']}%',
      );
    }
    if (predictions.isEmpty) return predictions;

    // ── Domain Rule 1: APW Larvae always wins over White Grub ──
    final hasApwLarvae = predictions.any((p) => p['class_id'] == 1);
    final hasWhiteGrub = predictions.any((p) => p['class_id'] == 6);
    if (hasApwLarvae && hasWhiteGrub) {
      predictions.removeWhere((p) => p['class_id'] == 6);
      debugPrint('🤖 [TFLite] Domain: APW Larvae wins — removed White Grub');
    }

    // ── Domain Rule 2: Brontispa Adult vs Brontispa Pupa ──
    // Life stages of the same pest — keep the higher-confidence detection.
    final hasBrontispa = predictions.any((p) => p['class_id'] == 2);
    final hasBrontispaPupa = predictions.any((p) => p['class_id'] == 3);
    if (hasBrontispa && hasBrontispaPupa) {
      final bConf =
          predictions.firstWhere(
            (p) => p['class_id'] == 2,
          )['confidence']
          as double;
      final pConf =
          predictions.firstWhere(
            (p) => p['class_id'] == 3,
          )['confidence']
          as double;
      if (pConf >= bConf) {
        predictions.removeWhere((p) => p['class_id'] == 2);
        debugPrint(
          '🤖 [TFLite] Domain: Brontispa Pupa wins ($pConf% >= $bConf%)',
        );
      } else {
        predictions.removeWhere((p) => p['class_id'] == 3);
        debugPrint(
          '🤖 [TFLite] Domain: Brontispa Adult wins ($bConf% > $pConf%)',
        );
      }
    }

    return predictions;
  }

'''

NEW_PREDICT_OUTPUT_SECTION = '''      debugPrint('🤖 [TFLite] Inference complete! ✅');

      // ── YOLO26s end2end output: [1, 300, 6] ──
      // Read raw bytes directly (bypasses tflite_flutter copyTo issues).
      final rawOutputBytes = _interpreter!.getOutputTensor(0).data;
      final rawOutputFloats = rawOutputBytes.buffer.asFloat32List();
      debugPrint(
        '🤖 [TFLite] Raw output: ${rawOutputFloats.length} floats '
        '(expected ${maxDetections * 6} for [300, 6])',
      );

      // Quick sanity: find max confidence across all 300 slots
      double maxConf = 0.0;
      for (int d = 0; d < maxDetections; d++) {
        final c = rawOutputFloats[d * 6 + 4];
        if (c > maxConf) maxConf = c;
      }
      debugPrint(
        '🤖 [TFLite] Max conf across $maxDetections detections: '
        '${(maxConf * 100).toStringAsFixed(2)}%',
      );

      final predictions = _processEnd2EndOutput(
        rawOutputFloats,
        confidenceThreshold,
      );
'''

NEW_POSTFILTER_SECTION = '''      debugPrint(
        '🤖 [TFLite] Found ${predictions.length} detections above '
        '${(confidenceThreshold * 100).toStringAsFixed(0)}% threshold',
      );

      if (predictions.isEmpty) {
        debugPrint('🤖 [TFLite] ❌ No pests detected - returning OUT_OF_SCOPE');
        return {
          'success': true,
          'status': 'OUT_OF_SCOPE',
          'message': 'No coconut pests detected in this image',
          'predictions': [],
          'best_match': null,
          'risk_level': 'out-of-scope',
          'offline': true,
        };
      }

      final bestMatch = predictions.first;
'''

with open(DART_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Original file: {len(content)} chars, {content.count(chr(10))} lines")

# ── Step 1: Remove _sigmoid + replace _processYoloOutput with _processEnd2EndOutput ──
import re

# Find the start of _sigmoid
sigmoid_start = content.find('  /// Apply sigmoid function')
if sigmoid_start == -1:
    print("ERROR: _sigmoid not found")
else:
    print(f"Found _sigmoid at char {sigmoid_start}")

# Find the end of _processYoloOutput (last return predictions; before predict())
# We find "    return predictions;\n  }\n\n  /// Run pest detection"
process_end_marker = '    return predictions;\n  }\n\n  /// Run pest detection'
process_end_idx = content.find(process_end_marker)
if process_end_idx == -1:
    print("ERROR: _processYoloOutput end marker not found")
else:
    # End is after "    return predictions;\n  }\n"
    process_end = process_end_idx + len('    return predictions;\n  }\n')
    print(f"Found _processYoloOutput end at char {process_end}")

if sigmoid_start != -1 and process_end_idx != -1:
    old_methods = content[sigmoid_start:process_end]
    print(f"Replacing {len(old_methods)} chars ({old_methods.count(chr(10))} lines) with new method")
    content = content[:sigmoid_start] + NEW_PROCESS_METHOD + content[process_end:]
    print(f"After step 1: {content.count(chr(10))} lines")

# ── Step 2: Replace output-reading section in predict() ──
# Old: from "      debugPrint('🤖 [TFLite] Inference complete! ✅');\n"
#      through "      final predictions = _processEnd2EndOutput(\n...      );\n"
# But after step 1 the file content changed. Let's find the right boundaries.

# Find inference-complete marker
inf_complete = "      debugPrint('🤖 [TFLite] Inference complete! ✅');"
inf_idx = content.find(inf_complete)
if inf_idx == -1:
    print("ERROR: inference complete marker not found")
else:
    print(f"Found inference complete at char {inf_idx}")

# Find the end of the old "found N predictions above" section that follows the old parsing
old_found_marker = "      debugPrint(\n        '🤖 [TFLite] Found ${predictions.length} predictions above '\n        '${(confidenceThreshold * 100).toStringAsFixed(0)}% threshold',\n      );"
old_found_idx = content.find(old_found_marker)
if old_found_idx == -1:
    print("ERROR: 'Found predictions' marker not found — searching alternatives")
    # Try another common text
    old_found_marker2 = "      debugPrint(\n        '🤖 [TFLite] Found ${predictions.length} predictions above "
    old_found_idx = content.find(old_found_marker2)
    if old_found_idx == -1:
        print("ERROR: alternative marker also not found")
    else:
        print(f"Found alternative marker at {old_found_idx}")

if inf_idx != -1 and old_found_idx != -1:
    # Replace from inf_complete through to (but not including) old_found_marker
    old_output_section = content[inf_idx:old_found_idx]
    print(f"Replacing output section: {len(old_output_section)} chars ({old_output_section.count(chr(10))} lines)")
    content = (content[:inf_idx] + NEW_PREDICT_OUTPUT_SECTION + '\n' +
               content[old_found_idx:])
    print(f"After step 2: {content.count(chr(10))} lines")

# ── Step 3: Replace old post-filter section (minConfidencePercent etc.) ──
# Find the "Found N predictions" block through "final bestMatch = predictions.first;"
old_postfilter_start = "      debugPrint(\n        '🤖 [TFLite] Found ${predictions.length} detections above '"
old_postfilter_end_marker = "      final bestMatch = predictions.first;"

pf_start = content.find(old_postfilter_start)
best_match_idx = content.find(old_postfilter_end_marker)

if pf_start != -1 and best_match_idx != -1:
    old_pf = content[pf_start:best_match_idx + len(old_postfilter_end_marker)]
    print(f"Replacing post-filter section: {len(old_pf)} chars")
    # Check if the old section contains minConfidencePercent (means it hasn't been cleaned)
    if 'minConfidencePercent' in old_pf or 'minConfidenceThreshold' in old_pf:
        # Replace entire section
        content = content[:pf_start] + NEW_POSTFILTER_SECTION + content[best_match_idx + len(old_postfilter_end_marker):]
        print("  ✅ Replaced post-filter section (had old minConfidence logic)")
    else:
        print("  ℹ️  Post-filter section already clean, keeping as-is")
else:
    print(f"Post-filter section: pf_start={pf_start}, best_match_idx={best_match_idx}")

# ── Step 4: Remove now-unused minConfidencePercent check if still present ──
# Find and remove the block: "if (bestConfidence < minConfidencePercent) {" block
min_conf_check = "      // Post-filter: require minimum confidence"
if min_conf_check in content:
    # Find start
    mc_start = content.find(min_conf_check)
    # Find end (the matching closing brace + blank line)
    mc_end_marker = "          'offline': true,\n        };\n      }\n"
    mc_end = content.find(mc_end_marker, mc_start)
    if mc_end != -1:
        mc_end += len(mc_end_marker)
        old_mc = content[mc_start:mc_end]
        print(f"Removing minConfidencePercent block: {len(old_mc)} chars")
        content = content[:mc_start] + content[mc_end:]

# Write back
with open(DART_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nFinal file: {len(content)} chars, {content.count(chr(10))} lines")
print("✅ Done!")
