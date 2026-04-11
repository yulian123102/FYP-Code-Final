import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter/foundation.dart' show mapEquals;
import 'painters.dart';

void main() => runApp(const WordProblemApp());

class WordProblemApp extends StatelessWidget {
  const WordProblemApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Word Problem Modeler',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        textTheme: GoogleFonts.interTextTheme(),
        useMaterial3: true,
        colorSchemeSeed: Colors.indigo,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  // Adjust if your backend is remote
  final String baseUrl = "http://127.0.0.1:8000";

  final TextEditingController _question = TextEditingController(text:
      "Esther had 157 and Fran had 100. They both spent the same amount on a blouse. "
      "After spending, the ratio of Esther to Fran is 5:2. How much did each blouse cost?");

  Map<String, dynamic>? _slots;        // result of /classify_extract
  Map<String, dynamic>? _solve;        // result of /solve (answer, steps_markdown, diagram_spec)
  String? _category;                   // selected category
  bool _loading = false;
  String? _error;

  Future<void> _classifyExtract() async {
    setState(() { _loading = true; _error = null; _slots = null; _solve = null; });
    try {
      final r = await http.post(Uri.parse("$baseUrl/classify_extract"),
        headers: {"Content-Type":"application/json"},
        body: jsonEncode({"question_text": _question.text}),
      );
      if (r.statusCode != 200) {
        setState(() => _error = "classify_extract ${r.statusCode}: ${r.body}");
        return;
      }
      final obj = jsonDecode(r.body);
      _category = obj["category"];
      _slots = obj["slots"];
      setState(() {});
    } catch (e) {
      setState(() => _error = "Failed: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _solveNow() async {
    if (_slots == null || _category == null) {
      setState(() => _error = "Run classify_extract first.");
      return;
    }
    setState(() { _loading = true; _error = null; _solve = null; });
    try {
      final r = await http.post(Uri.parse("$baseUrl/solve"),
        headers: {"Content-Type":"application/json"},
        body: jsonEncode({"category": _category, "slots": _slots}),
      );
      if (r.statusCode != 200) {
        setState(() => _error = "solve ${r.statusCode}: ${r.body}");
        return;
      }
      _solve = jsonDecode(r.body);
      setState(() {});
    } catch (e) {
      setState(() => _error = "Failed: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  /// Dispatches to the correct CustomPainter based on diagram_spec["type"].
  CustomPainter? _getDiagramPainter(Map<String, dynamic> diag) {
    if (diag['type'] == 'before_after') {
      return BeforeAfterPainter(diagramSpec: diag);
    }
    return getPainterForSpec(diag);
  }

  @override
  Widget build(BuildContext context) {
    final diag = _solve?["diagram_spec"] as Map<String, dynamic>?;

    return Scaffold(
      appBar: AppBar(title: const Text("Word Problem Modeler (MVP)")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          // Problem input
          TextField(
            controller: _question,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: "Paste a word problem",
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Row(children: [
            ElevatedButton(
              onPressed: _loading ? null : _classifyExtract,
              child: Text(_loading ? "Working..." : "Classify & Extract"),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: _loading ? null : _solveNow,
              child: Text(_loading ? "Working..." : "Solve & Render"),
            ),
          ]),
          const SizedBox(height: 8),

          // Status
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          if (_slots != null) Align(
            alignment: Alignment.centerLeft,
            child: Text("Category: $_category   (slots extracted ✓)"),
          ),
          const SizedBox(height: 8),

          // Main content
          Expanded(
            child: Row(
              children: [
                // Diagram
                Expanded(
                  flex: 1,
                  child: Card(
                    elevation: 1,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Model Diagram"),
                          const SizedBox(height: 8),
                          Expanded(
                            child: Container(
                              color: Colors.white,
                              child: ClipRect(
                                child: CustomPaint(
                                  painter: diag != null
                                      ? _getDiagramPainter(diag)
                                      : null,
                                  child: const SizedBox.expand(),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),

                // Steps
                Expanded(
                  flex: 1,
                  child: Card(
                    elevation: 1,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Solution Steps"),
                          const SizedBox(height: 8),
                          Expanded(
                            child: _solve?["steps_markdown"] != null
                                ? Markdown(
                                    data: _solve!["steps_markdown"],
                                    padding: EdgeInsets.zero,
                                  )
                                : const Center(child: Text("Run Solve to see steps")),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              ],
            ),
          ),

          // Answer summary
          if (_solve?["answer"] != null) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Text("Answer: ${jsonEncode(_solve!["answer"])}"),
            ),
          ],
        ]),
      ),
    );
  }
}

/// Simple painter for "before_after" diagram_spec from backend.
/// Expects:
///   {
///     "type":"before_after",
///     "bars": {
///       "before":[{"label":A,"value":...},{"label":B,"value":...}],
///       "after":[{"label":A,"units":ra,"unitValue":u},{"label":B,"units":rb,"unitValue":u}]
///     },
///     "action":"spend_equal" | "transfer",
///     "equal_spend": true?, "amount": number?,
///     "transfer": {"amount": number, "from": name, "to": name}?
///   }
class BeforeAfterPainter extends CustomPainter {
  final Map<String, dynamic> diagramSpec;
  BeforeAfterPainter({required this.diagramSpec});

  @override
  void paint(Canvas canvas, Size size) {
    if (diagramSpec["type"] != "before_after") return;

    final bars = diagramSpec["bars"] as Map<String, dynamic>;
    final before = (bars["before"] as List).cast<Map>();
    final after = (bars["after"] as List).cast<Map>();

    // Layout constants
    final pad = 16.0;
    final barH = 22.0;
    final gapV = 18.0;
    //final unitTick = 6.0;

    final paintBar = Paint()..style = PaintingStyle.fill;
    final paintStroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0
      ..color = Colors.black;
    final labelStyle = TextStyle(color: Colors.black87, fontSize: 12);

    // Regions
    final width = size.width - 2 * pad;
    final left = pad;
    double top = pad;

    // Find max value for "before" scale
    double maxBefore = 1;
    for (final b in before) {
      final v = (b["value"] as num?)?.toDouble() ?? 0;
      if (v > maxBefore) maxBefore = v;
    }

    // Draw BEFORE title
    _drawText(canvas, "Before", Offset(left, top - 2), style: const TextStyle(fontWeight: FontWeight.bold));
    top += 16;

    // Draw BEFORE bars (two rows)
    for (final b in before) {
      final label = b["label"].toString();
      final v = (b["value"] as num).toDouble();
      final w = (v / maxBefore) * width;
      // label
      _drawText(canvas, "$label: $v", Offset(left, top - 14), style: labelStyle);
      // bar
      paintBar.color = Colors.indigo.shade200;
      final rect = Rect.fromLTWH(left, top, w, barH);
      canvas.drawRect(rect, paintBar);
      canvas.drawRect(rect, paintStroke);
      top += barH + gapV;
    }

    // Spacer
    top += 8;

    // Draw AFTER title
    _drawText(canvas, "After (ratio units)", Offset(left, top - 2), style: const TextStyle(fontWeight: FontWeight.bold));
    top += 16;

    // Determine unit length for AFTER (units * unitValue)
    double maxAfter = 1;
    for (final a in after) {
      final units = (a["units"] as num).toDouble();
      final unitValue = (a["unitValue"] as num).toDouble();
      final val = units * unitValue;
      if (val > maxAfter) maxAfter = val;
    }

    // Draw AFTER bars with unit segmentation
    for (final a in after) {
      final label = a["label"].toString();
      final units = (a["units"] as num).toDouble();
      final unitValue = (a["unitValue"] as num).toDouble();
      final total = units * unitValue;
      final w = (total / maxAfter) * width;

      _drawText(canvas, "$label: $units units × ${_fmt(unitValue)}", Offset(left, top - 14), style: labelStyle);

      // outer bar
      final rect = Rect.fromLTWH(left, top, w, barH);
      paintBar.color = Colors.teal.shade200;
      canvas.drawRect(rect, paintBar);
      canvas.drawRect(rect, paintStroke);

      // unit ticks
      final unitPix = w / (units <= 0 ? 1 : units);
      for (int k = 1; k < units.round(); k++) {
        final x = left + k * unitPix;
        canvas.drawLine(Offset(x, top), Offset(x, top + barH), paintStroke);
      }

      // annotate total
      _drawText(canvas, _fmt(total), Offset(left + w + 6, top + 2), style: labelStyle);

      top += barH + gapV;
    }

    // Draw equal-spend or transfer annotation if present
    final isEqualSpend = diagramSpec["equal_spend"] == true;
    final action = diagramSpec["action"];
    if (isEqualSpend && diagramSpec["amount"] != null) {
      _drawText(canvas, "Both spent = ${_fmt((diagramSpec["amount"] as num).toDouble())}",
          Offset(left, top), style: const TextStyle(color: Colors.black87));
    } else if (action == "transfer" && diagramSpec["transfer"] != null) {
      final tr = diagramSpec["transfer"] as Map;
      _drawText(canvas, "Transfer ${_fmt((tr["amount"] as num).toDouble())} from ${tr["from"]} to ${tr["to"]}",
          Offset(left, top), style: const TextStyle(color: Colors.black87));
    }
  }

  @override
  bool shouldRepaint(covariant BeforeAfterPainter oldDelegate) {
    return !mapEquals(oldDelegate.diagramSpec, diagramSpec);
    // Redraw when spec changes
  }

  void _drawText(Canvas canvas, String text, Offset p, {TextStyle? style}) {
    final tp = TextPainter(
      text: TextSpan(text: text, style: style ?? const TextStyle(color: Colors.black)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, p);
  }

  String _fmt(double v) {
    // nice number formatting with trimming
    final s = v.toStringAsFixed(v.truncateToDouble() == v ? 0 : 2);
    return s;
  }
}
