/// painters.dart — CustomPainter classes for all 15 word-problem diagram types.
/// Each painter takes a diagram_spec Map from the backend and renders MOE/PSLE-style
/// model diagrams using Canvas drawing primitives.
import 'package:flutter/material.dart';

// ─── Shared helpers ───────────────────────────────────────────────
void _drawText(Canvas canvas, String text, Offset p, {TextStyle? style}) {
  final tp = TextPainter(
    text: TextSpan(text: text, style: style ?? const TextStyle(color: Colors.black, fontSize: 12)),
    textDirection: TextDirection.ltr,
  )..layout();
  tp.paint(canvas, p);
}

String _fmt(double v) {
  final s = v.toStringAsFixed(v.truncateToDouble() == v ? 0 : 2);
  return s;
}

// ═══════════════════════════════════════════════════════════════════
//  1. FRACTIONS OF A WHOLE
// ═══════════════════════════════════════════════════════════════════
class FractionsWholePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  FractionsWholePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 32.0;
    final den = (spec['fraction_den'] as num?)?.toInt() ?? 4;
    final num_ = (spec['fraction_num'] as num?)?.toInt() ?? 1;
    final w = size.width - 2 * pad;
    final segW = w / den;

    _drawText(canvas, 'Fraction: $num_/$den of ${spec["entity"] ?? "items"}',
        Offset(pad, pad), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));

    final top = pad + 24;
    final fill = Paint()..color = Colors.indigo.shade300;
    final empty = Paint()..color = Colors.grey.shade200;
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.5..color = Colors.black;

    for (int i = 0; i < den; i++) {
      final rect = Rect.fromLTWH(pad + i * segW, top, segW, barH);
      canvas.drawRect(rect, i < num_ ? fill : empty);
      canvas.drawRect(rect, stroke);
      _drawText(canvas, '${i + 1}', Offset(pad + i * segW + segW / 2 - 4, top + barH + 4));
    }
    // Bracket for shaded portion
    final bracketY = top + barH + 22;
    final bracketPaint = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.5..color = Colors.indigo;
    canvas.drawLine(Offset(pad, bracketY), Offset(pad + num_ * segW, bracketY), bracketPaint);
    _drawText(canvas, '= ${spec["known_value"] ?? "?"}', Offset(pad + num_ * segW / 2 - 10, bracketY + 4),
        style: TextStyle(color: Colors.indigo.shade700, fontSize: 12));
  }

  @override
  bool shouldRepaint(covariant FractionsWholePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  2. DIFFERENCE (MORE / LESS) — comparison bars
// ═══════════════════════════════════════════════════════════════════
class DifferencePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  DifferencePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 28.0;
    final gap = 24.0;
    final vals = (spec['values'] as Map<String, dynamic>?) ?? {};
    final entities = (spec['entities'] as List?)?.cast<String>() ?? vals.keys.toList();
    final diff = (spec['difference'] as num?)?.toDouble() ?? 0;
    final maxVal = vals.values.fold<double>(1, (m, v) => (v as num).toDouble() > m ? (v as num).toDouble() : m);
    final w = size.width - 2 * pad - 60;

    _drawText(canvas, 'Comparison Model', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 24;
    final fill1 = Paint()..color = Colors.teal.shade300;
    final fill2 = Paint()..color = Colors.orange.shade300;
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.2..color = Colors.black;

    for (int i = 0; i < entities.length && i < 2; i++) {
      final name = entities[i];
      final v = (vals[name] as num?)?.toDouble() ?? 0;
      final bw = (v / maxVal) * w;
      _drawText(canvas, '$name:', Offset(pad, top - 14));
      final rect = Rect.fromLTWH(pad + 50, top, bw, barH);
      canvas.drawRect(rect, i == 0 ? fill1 : fill2);
      canvas.drawRect(rect, stroke);
      _drawText(canvas, _fmt(v), Offset(pad + 50 + bw + 6, top + 6));
      top += barH + gap;
    }
    // Difference bracket
    if (entities.length == 2) {
      final v1 = (vals[entities[0]] as num?)?.toDouble() ?? 0;
      final v2 = (vals[entities[1]] as num?)?.toDouble() ?? 0;
      final shorter = v1 < v2 ? v1 : v2;
      final bw = (shorter / maxVal) * w;
      final bracketX = pad + 50 + bw;
      final bracketPaint = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.5..color = Colors.red;
      canvas.drawLine(Offset(bracketX, pad + 24), Offset(bracketX, pad + 24 + barH + gap + barH), bracketPaint);
      _drawText(canvas, 'diff = ${_fmt(diff)}', Offset(bracketX + 6, pad + 24 + barH),
          style: TextStyle(color: Colors.red.shade700, fontSize: 11));
    }
  }

  @override
  bool shouldRepaint(covariant DifferencePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  3. MULTIPLE (TIMES AS MANY) — stacked bars
// ═══════════════════════════════════════════════════════════════════
class MultiplePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  MultiplePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 28.0;
    final gap = 22.0;
    final vals = (spec['values'] as Map<String, dynamic>?) ?? {};
    final entities = (spec['entities'] as List?)?.cast<String>() ?? vals.keys.toList();
    final mult = (spec['multiplier'] as num?)?.toDouble() ?? 1;
    final maxVal = vals.values.fold<double>(1, (m, v) => (v as num).toDouble() > m ? (v as num).toDouble() : m);
    final w = size.width - 2 * pad - 60;

    _drawText(canvas, 'Multiple Model (×${_fmt(mult)})', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 24;
    final colors = [Colors.indigo.shade300, Colors.amber.shade300];
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.2..color = Colors.black;

    for (int i = 0; i < entities.length && i < 2; i++) {
      final name = entities[i];
      final v = (vals[name] as num?)?.toDouble() ?? 0;
      final bw = (v / maxVal) * w;
      _drawText(canvas, '$name:', Offset(pad, top - 14));
      final fill = Paint()..color = colors[i % 2];
      // Draw segments for the larger bar
      if (name == spec['who_is_more'] && mult > 1) {
        final segW = bw / mult;
        for (int k = 0; k < mult.round(); k++) {
          final r = Rect.fromLTWH(pad + 50 + k * segW, top, segW, barH);
          canvas.drawRect(r, fill);
          canvas.drawRect(r, stroke);
        }
      } else {
        final rect = Rect.fromLTWH(pad + 50, top, bw, barH);
        canvas.drawRect(rect, fill);
        canvas.drawRect(rect, stroke);
      }
      _drawText(canvas, _fmt(v), Offset(pad + 50 + bw + 6, top + 6));
      top += barH + gap;
    }
  }

  @override
  bool shouldRepaint(covariant MultiplePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  4. RATIO — segmented bars
// ═══════════════════════════════════════════════════════════════════
class RatioPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  RatioPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 28.0;
    final gap = 22.0;
    final ratioMap = (spec['ratio'] as Map<String, dynamic>?) ?? {};
    final entities = (spec['entities'] as List?)?.cast<String>() ?? ratioMap.keys.toList();
    final unit = (spec['unit_value'] as num?)?.toDouble() ?? 1;
    final maxParts = ratioMap.values.fold<double>(0, (m, v) => (v as num).toDouble() > m ? (v as num).toDouble() : m);
    final w = size.width - 2 * pad - 60;

    _drawText(canvas, 'Ratio Model  (1 unit = ${_fmt(unit)})', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 24;
    final colors = [Colors.teal.shade300, Colors.purple.shade200, Colors.orange.shade300];
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.2..color = Colors.black;

    for (int i = 0; i < entities.length; i++) {
      final name = entities[i];
      final parts = (ratioMap[name] as num?)?.toDouble() ?? 1;
      final segW = w / maxParts;
      _drawText(canvas, '$name:', Offset(pad, top - 14));
      final fill = Paint()..color = colors[i % colors.length];
      for (int k = 0; k < parts.round(); k++) {
        final r = Rect.fromLTWH(pad + 50 + k * segW, top, segW, barH);
        canvas.drawRect(r, fill);
        canvas.drawRect(r, stroke);
      }
      _drawText(canvas, '${parts.round()} units = ${_fmt(parts * unit)}',
          Offset(pad + 50 + parts * segW + 6, top + 6));
      top += barH + gap;
    }
  }

  @override
  bool shouldRepaint(covariant RatioPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  6. EQUAL SHARE EXCESS/SHORTAGE
// ═══════════════════════════════════════════════════════════════════
class EqualSharePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  EqualSharePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 24.0;
    final people = (spec['people'] as num?)?.toDouble() ?? 0;
    final items = (spec['items'] as num?)?.toDouble() ?? 0;
    final shareA = (spec['share_a'] as num?)?.toDouble() ?? 0;
    final excess = (spec['excess'] as num?)?.toDouble() ?? 0;
    final shortage = (spec['shortage'] as num?)?.toDouble() ?? 0;
    final w = size.width - 2 * pad;

    _drawText(canvas, 'Equal Share Model', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 28;
    _drawText(canvas, 'Scenario A: $shareA each, $excess left', Offset(pad, top));
    top += 18;
    final fillA = Paint()..color = Colors.green.shade200;
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.black;
    final usedW = (shareA * people / items) * w;
    canvas.drawRect(Rect.fromLTWH(pad, top, usedW, barH), fillA);
    canvas.drawRect(Rect.fromLTWH(pad, top, usedW, barH), stroke);
    // excess portion
    final excessW = (excess / items) * w;
    final exPaint = Paint()..color = Colors.green.shade100;
    canvas.drawRect(Rect.fromLTWH(pad + usedW, top, excessW, barH), exPaint);
    canvas.drawRect(Rect.fromLTWH(pad + usedW, top, excessW, barH), stroke);
    _drawText(canvas, '+$excess', Offset(pad + usedW + 2, top + 4));

    top += barH + 24;
    _drawText(canvas, 'People = ${_fmt(people)}, Items = ${_fmt(items)}', Offset(pad, top),
        style: TextStyle(color: Colors.indigo.shade700, fontSize: 13));
  }

  @override
  bool shouldRepaint(covariant EqualSharePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  7. GROUPING WITH REMAINDER
// ═══════════════════════════════════════════════════════════════════
class GroupingPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  GroupingPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final groupSize = (spec['group_size'] as num?)?.toInt() ?? 3;
    final remainder = (spec['remainder'] as num?)?.toInt() ?? 0;
    final ans = (spec['answer'] as Map<String, dynamic>?) ?? {};
    final groups = (ans['groups'] as num?)?.toInt() ?? 2;
    final r = 14.0;

    _drawText(canvas, 'Grouping Model (size=$groupSize, r=$remainder)', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double x = pad;
    double y = pad + 32;
    final fill = Paint()..color = Colors.blue.shade200;
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.black;
    final maxGroups = groups > 8 ? 8 : groups; // cap visual
    for (int g = 0; g < maxGroups; g++) {
      // draw circle group
      final cx = x + r + 4;
      final cy = y + r;
      canvas.drawCircle(Offset(cx, cy), r, fill);
      canvas.drawCircle(Offset(cx, cy), r, stroke);
      _drawText(canvas, '$groupSize', Offset(cx - 5, cy - 6));
      x += r * 2 + 12;
      if (x + r * 2 > size.width - pad) { x = pad; y += r * 2 + 12; }
    }
    // remainder dots
    if (remainder > 0) {
      final rFill = Paint()..color = Colors.orange.shade300;
      for (int i = 0; i < remainder && i < 10; i++) {
        canvas.drawCircle(Offset(x + 8 + i * 16, y + r), 6, rFill);
        canvas.drawCircle(Offset(x + 8 + i * 16, y + r), 6, stroke);
      }
      _drawText(canvas, 'r=$remainder', Offset(x, y + r * 2 + 4));
    }
  }

  @override
  bool shouldRepaint(covariant GroupingPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  8. PRICE × QUANTITY — table/bars
// ═══════════════════════════════════════════════════════════════════
class PriceQtyPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  PriceQtyPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final items = (spec['items'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final results = (spec['results'] as Map<String, dynamic>?) ?? {};
    final barH = 28.0;
    final gap = 28.0;
    final w = size.width - 2 * pad - 100;
    double maxTotal = 1;
    for (final it in items) {
      final up = (it['unit_price'] as num?)?.toDouble() ?? 0;
      final q = (it['quantity'] as num?)?.toDouble() ?? 0;
      final t = (it['total'] as num?)?.toDouble() ?? (up * q);
      if (t > maxTotal) maxTotal = t;
    }
    _drawText(canvas, 'Price × Quantity', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 24;
    final colors = [Colors.cyan.shade300, Colors.pink.shade200, Colors.lime.shade300, Colors.amber.shade200];
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.2..color = Colors.black;
    final dividerPaint = Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.black54;

    for (int i = 0; i < items.length; i++) {
      final it = items[i];
      final name = it['name'] ?? 'Item';
      final up = (it['unit_price'] as num?)?.toDouble() ?? 0;
      final q = (it['quantity'] as num?)?.toDouble() ?? 1;
      final qInt = q.round().clamp(1, 20);
      final t = (it['total'] as num?)?.toDouble() ?? (up * q);
      final bw = (t / maxTotal) * w;
      _drawText(canvas, '$name:', Offset(pad, top - 14));
      final fill = Paint()..color = colors[i % colors.length];

      // Draw the full bar outline
      final fullRect = Rect.fromLTWH(pad + 60, top, bw, barH);
      canvas.drawRect(fullRect, fill);
      canvas.drawRect(fullRect, stroke);

      // Draw segment dividers (quantity segments)
      final segW = bw / qInt;
      for (int s = 1; s < qInt; s++) {
        final x = pad + 60 + segW * s;
        canvas.drawLine(Offset(x, top), Offset(x, top + barH), dividerPaint);
      }

      // Label each segment with unit price (if fits)
      if (segW > 30 && up > 0) {
        for (int s = 0; s < qInt; s++) {
          final sx = pad + 60 + segW * s + segW / 2 - 12;
          _drawText(canvas, '\$${_fmt(up)}', Offset(sx, top + 6),
              style: const TextStyle(fontSize: 9, color: Colors.black87));
        }
      }

      // Total label on the right
      _drawText(canvas, '\$${_fmt(t)}  (×$qInt)', Offset(pad + 60 + bw + 6, top + 6));
      top += barH + gap;
    }
    final grand = (results['grand_total'] as num?)?.toDouble() ?? 0;
    _drawText(canvas, 'Grand Total = \$${_fmt(grand)}', Offset(pad, top),
        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo.shade700, fontSize: 13));
  }

  @override
  bool shouldRepaint(covariant PriceQtyPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  9. COINS / NOTES — stacked icons
// ═══════════════════════════════════════════════════════════════════
class CoinsNotesPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  CoinsNotesPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final denoms = (spec['denominations'] as List?)?.cast<num>() ?? [];
    final ans = (spec['answer'] as Map<String, dynamic>?) ?? {};

    _drawText(canvas, 'Coins / Notes Model', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 28;
    final r = 18.0;
    final colors = [Colors.amber.shade400, Colors.grey.shade400, Colors.brown.shade300];
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.2..color = Colors.black;

    for (int i = 0; i < denoms.length; i++) {
      final d = denoms[i].toDouble();
      final key = '\$$d';
      final count = (ans[key] as num?)?.toDouble() ?? 0;
      final fill = Paint()..color = colors[i % colors.length];
      _drawText(canvas, '\$$d:', Offset(pad, top + 4));
      final maxShow = count.round().clamp(0, 12);
      for (int k = 0; k < maxShow; k++) {
        canvas.drawCircle(Offset(pad + 50 + k * (r + 4), top + r / 2 + 4), r / 2, fill);
        canvas.drawCircle(Offset(pad + 50 + k * (r + 4), top + r / 2 + 4), r / 2, stroke);
      }
      _drawText(canvas, '×${_fmt(count)}', Offset(pad + 50 + maxShow * (r + 4) + 4, top + 4));
      top += r + 16;
    }
  }

  @override
  bool shouldRepaint(covariant CoinsNotesPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
// 10. SPEED–DISTANCE–TIME — distance line
// ═══════════════════════════════════════════════════════════════════
class SDTPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  SDTPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final w = size.width - 2 * pad;
    final speed = (spec['speed'] as num?)?.toDouble() ?? 0;
    final dist = (spec['distance'] as num?)?.toDouble() ?? 0;
    final time = (spec['time'] as num?)?.toDouble() ?? 0;
    final find = (spec['find'] as String?) ?? 'distance';
    final answer = (spec['answer'] as Map<String, dynamic>?) ?? {};

    _drawText(canvas, 'Speed–Distance–Time', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));

    final y = pad + 50;
    final linePaint = Paint()..strokeWidth = 2..color = Colors.indigo;
    final arrowPaint = Paint()..color = Colors.indigo..style = PaintingStyle.fill;
    // Draw line
    canvas.drawLine(Offset(pad, y), Offset(pad + w, y), linePaint);
    // Start marker
    canvas.drawCircle(Offset(pad, y), 5, arrowPaint);
    // End marker
    canvas.drawCircle(Offset(pad + w, y), 5, arrowPaint);
    // Labels
    _drawText(canvas, 'Start', Offset(pad - 10, y + 10));
    _drawText(canvas, 'End', Offset(pad + w - 10, y + 10));

    // Distance label above the line
    final distVal = find == 'distance' ? (answer['distance'] as num?)?.toDouble() ?? dist : dist;
    _drawText(canvas, 'Distance = ${_fmt(distVal)} km', Offset(pad + w / 2 - 50, y - 24),
        style: TextStyle(fontSize: 13, color: Colors.indigo.shade700));

    // Speed and Time labels below the line — highlight the answer
    final normalStyle = const TextStyle(fontSize: 12, color: Colors.black87);
    final answerStyle = TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.red.shade700);

    final speedVal = find == 'speed' ? (answer['speed'] as num?)?.toDouble() ?? speed : speed;
    final timeVal = find == 'time' ? (answer['time'] as num?)?.toDouble() ?? time : time;

    // Speed label
    final speedLabel = find == 'speed'
        ? 'Ans: Speed = ${_fmt(speedVal)} km/h'
        : 'Speed = ${_fmt(speedVal)} km/h';
    _drawText(canvas, speedLabel, Offset(pad, y + 30),
        style: find == 'speed' ? answerStyle : normalStyle);

    // Time label
    final timeLabel = find == 'time'
        ? 'Ans: Time = ${_fmt(timeVal)} h'
        : 'Time = ${_fmt(timeVal)} h';
    _drawText(canvas, timeLabel, Offset(pad + w / 2, y + 30),
        style: find == 'time' ? answerStyle : normalStyle);

    // If finding distance, add a prominent answer label below
    if (find == 'distance') {
      _drawText(canvas, 'Ans: Distance = ${_fmt(distVal)} km', Offset(pad, y + 58),
          style: answerStyle);
    }
  }

  @override
  bool shouldRepaint(covariant SDTPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
// 11. WORK / RATE — bar chart
// ═══════════════════════════════════════════════════════════════════
class WorkRatePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  WorkRatePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 24.0;
    final gap = 18.0;
    final workers = (spec['workers'] as List?)?.cast<String>() ?? [];
    final times = (spec['times'] as Map<String, dynamic>?) ?? {};
    final ans = (spec['answer'] as Map<String, dynamic>?) ?? {};
    final maxT = times.values.fold<double>(1, (m, v) => (v as num).toDouble() > m ? (v as num).toDouble() : m);
    final w = size.width - 2 * pad - 80;

    _drawText(canvas, 'Work Rate Model', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    double top = pad + 24;
    final colors = [Colors.teal.shade300, Colors.orange.shade300, Colors.purple.shade200];
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.black;

    for (int i = 0; i < workers.length; i++) {
      final name = workers[i];
      final t = (times[name] as num?)?.toDouble() ?? 0;
      final bw = (t / maxT) * w;
      _drawText(canvas, '$name:', Offset(pad, top - 14));
      final fill = Paint()..color = colors[i % colors.length];
      canvas.drawRect(Rect.fromLTWH(pad + 60, top, bw, barH), fill);
      canvas.drawRect(Rect.fromLTWH(pad + 60, top, bw, barH), stroke);
      _drawText(canvas, '${_fmt(t)}h', Offset(pad + 60 + bw + 6, top + 4));
      top += barH + gap;
    }
    final ct = ans['combined_time'];
    if (ct != null) {
      _drawText(canvas, 'Combined = ${_fmt((ct as num).toDouble())}h', Offset(pad, top),
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo.shade700, fontSize: 13));
    }
  }

  @override
  bool shouldRepaint(covariant WorkRatePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
// 12. AGE — timeline
// ═══════════════════════════════════════════════════════════════════
class AgePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  AgePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final w = size.width - 2 * pad;
    final entities = (spec['entities'] as List?)?.cast<String>() ?? [];
    final ages = (spec['ages_now'] as Map<String, dynamic>?) ?? {};
    final offset = (spec['offset'] as num?)?.toDouble() ?? 0;
    final ans = (spec['answer'] as Map<String, dynamic>?) ?? {};

    _drawText(canvas, 'Age Timeline', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));

    final lineY = pad + 50;
    final linePaint = Paint()..strokeWidth = 2..color = Colors.brown;
    canvas.drawLine(Offset(pad, lineY), Offset(pad + w, lineY), linePaint);

    // "Now" marker at midpoint
    final nowX = pad + w / 2;
    canvas.drawCircle(Offset(nowX, lineY), 5, Paint()..color = Colors.brown);
    _drawText(canvas, 'Now', Offset(nowX - 10, lineY + 10));

    // Future/past marker
    if (offset != 0) {
      final thenX = offset > 0 ? pad + w * 0.85 : pad + w * 0.15;
      canvas.drawCircle(Offset(thenX, lineY), 5, Paint()..color = Colors.indigo);
      final label = offset > 0 ? '+${_fmt(offset.abs())}y' : '-${_fmt(offset.abs())}y';
      _drawText(canvas, label, Offset(thenX - 12, lineY + 10));
    }

    double top = lineY + 34;
    for (final e in entities) {
      final ageNow = ages[e];
      final solved = ans[e];
      final display = ageNow ?? solved ?? '?';
      _drawText(canvas, '$e: $display years old now', Offset(pad, top));
      top += 18;
    }
  }

  @override
  bool shouldRepaint(covariant AgePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
// 13. PERCENTAGE CHANGE — bar with shaded portion
// ═══════════════════════════════════════════════════════════════════
class PercentagePainter extends CustomPainter {
  final Map<String, dynamic> spec;
  PercentagePainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final barH = 32.0;
    final w = size.width - 2 * pad;
    final original = (spec['original'] as num?)?.toDouble() ?? 100;
    final pct = (spec['percentage'] as num?)?.toDouble() ?? 0;
    final dir = spec['direction'] ?? 'increase';

    _drawText(canvas, 'Percentage ${dir == "increase" ? "Increase" : "Decrease"} (${_fmt(pct)}%)',
        Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));

    final top = pad + 30;
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.2..color = Colors.black;

    // Original bar (100%)
    _drawText(canvas, 'Original:', Offset(pad, top - 14));
    final origPaint = Paint()..color = Colors.blue.shade200;
    canvas.drawRect(Rect.fromLTWH(pad, top, w * 0.7, barH), origPaint);
    canvas.drawRect(Rect.fromLTWH(pad, top, w * 0.7, barH), stroke);
    _drawText(canvas, _fmt(original), Offset(pad + w * 0.7 + 6, top + 8));
    _drawText(canvas, '100%', Offset(pad + w * 0.35 - 14, top + 8));

    // Change portion
    final top2 = top + barH + 22;
    _drawText(canvas, dir == 'increase' ? 'After (+):' : 'After (−):', Offset(pad, top2 - 14));
    final changeFrac = pct / 100;
    if (dir == 'increase') {
      canvas.drawRect(Rect.fromLTWH(pad, top2, w * 0.7, barH), origPaint);
      final addPaint = Paint()..color = Colors.green.shade300;
      canvas.drawRect(Rect.fromLTWH(pad + w * 0.7, top2, w * 0.7 * changeFrac, barH), addPaint);
      canvas.drawRect(Rect.fromLTWH(pad, top2, w * 0.7 + w * 0.7 * changeFrac, barH), stroke);
      _drawText(canvas, '+${_fmt(pct)}%', Offset(pad + w * 0.7 + 2, top2 + 8),
          style: TextStyle(color: Colors.green.shade700, fontSize: 11));
    } else {
      final afterW = w * 0.7 * (1 - changeFrac);
      canvas.drawRect(Rect.fromLTWH(pad, top2, afterW, barH), origPaint);
      canvas.drawRect(Rect.fromLTWH(pad, top2, afterW, barH), stroke);
      final removedPaint = Paint()..color = Colors.red.shade100;
      canvas.drawRect(Rect.fromLTWH(pad + afterW, top2, w * 0.7 - afterW, barH), removedPaint);
      canvas.drawRect(Rect.fromLTWH(pad + afterW, top2, w * 0.7 - afterW, barH), stroke);
      _drawText(canvas, '-${_fmt(pct)}%', Offset(pad + afterW + 2, top2 + 8),
          style: TextStyle(color: Colors.red.shade700, fontSize: 11));
    }
  }

  @override
  bool shouldRepaint(covariant PercentagePainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
// 14. AREA / PERIMETER — shape outline
// ═══════════════════════════════════════════════════════════════════
class AreaPerimeterPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  AreaPerimeterPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final shape = spec['shape'] ?? 'rectangle';
    final ans = (spec['answer'] as Map<String, dynamic>?) ?? {};
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 2..color = Colors.indigo;
    final fill = Paint()..color = Colors.indigo.shade100;

    _drawText(canvas, 'Shape: ${shape[0].toUpperCase()}${shape.substring(1)}', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));

    final cx = size.width / 2;
    final cy = size.height / 2;

    if (shape == 'rectangle' || shape == 'composite') {
      final l = (spec['length'] as num?)?.toDouble() ?? 80;
      final w = (spec['width'] as num?)?.toDouble() ?? 50;
      final scale = (size.width - 2 * pad - 80) / (l > 0 ? l : 80);
      final drawW = l * scale;
      final drawH = w * scale;
      final rect = Rect.fromCenter(center: Offset(cx, cy), width: drawW.clamp(40, size.width - 60), height: drawH.clamp(30, size.height - 100));
      canvas.drawRect(rect, fill);
      canvas.drawRect(rect, stroke);
      _drawText(canvas, '${_fmt(l)}', Offset(rect.center.dx - 12, rect.bottom + 6));
      _drawText(canvas, '${_fmt(w)}', Offset(rect.right + 6, rect.center.dy - 6));
    } else if (shape == 'square') {
      final s = (spec['side'] as num?)?.toDouble() ?? 60;
      final drawS = (s * 2).clamp(40.0, size.width - 100);
      final rect = Rect.fromCenter(center: Offset(cx, cy), width: drawS, height: drawS);
      canvas.drawRect(rect, fill);
      canvas.drawRect(rect, stroke);
      _drawText(canvas, '${_fmt(s)}', Offset(rect.center.dx - 8, rect.bottom + 6));
    } else if (shape == 'triangle') {
      final b = (spec['base'] as num?)?.toDouble() ?? 80;
      final h = (spec['height'] as num?)?.toDouble() ?? 60;
      final scale = (size.width - 2 * pad - 80) / (b > 0 ? b : 80);
      final drawB = (b * scale).clamp(40.0, size.width - 80);
      final drawH = (h * scale).clamp(30.0, size.height - 100);
      final path = Path()
        ..moveTo(cx - drawB / 2, cy + drawH / 2)
        ..lineTo(cx + drawB / 2, cy + drawH / 2)
        ..lineTo(cx, cy - drawH / 2)
        ..close();
      canvas.drawPath(path, fill);
      canvas.drawPath(path, stroke);
      _drawText(canvas, 'b=${_fmt(b)}', Offset(cx - 16, cy + drawH / 2 + 6));
      _drawText(canvas, 'h=${_fmt(h)}', Offset(cx + 6, cy - 6));
    }
    // Answer
    String ansStr = ans.entries.map((e) => '${e.key}=${e.value}').join(', ');
    _drawText(canvas, ansStr, Offset(pad, size.height - pad - 16),
        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo.shade700, fontSize: 13));
  }

  @override
  bool shouldRepaint(covariant AreaPerimeterPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
// 15. TWO-SET OVERLAP — Venn diagram
// ═══════════════════════════════════════════════════════════════════
class TwoSetOverlapPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  TwoSetOverlapPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    final pad = 16.0;
    final labelA = spec['set_a_label'] ?? 'A';
    final labelB = spec['set_b_label'] ?? 'B';
    final onlyA = (spec['only_a'] as num?)?.toDouble() ?? 0;
    final onlyB = (spec['only_b'] as num?)?.toDouble() ?? 0;
    final both = (spec['both'] as num?)?.toDouble() ?? 0;
    final neither = (spec['neither'] as num?)?.toDouble();

    _drawText(canvas, 'Venn Diagram', Offset(pad, pad),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));

    final cx = size.width / 2;
    final cy = size.height / 2 + 10;
    final r = (size.width * 0.22).clamp(40.0, 120.0);
    final offset = r * 0.6;

    final paintA = Paint()..color = Colors.blue.withOpacity(0.25);
    final paintB = Paint()..color = Colors.red.withOpacity(0.25);
    final stroke = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.5..color = Colors.black;

    canvas.drawCircle(Offset(cx - offset, cy), r, paintA);
    canvas.drawCircle(Offset(cx - offset, cy), r, stroke);
    canvas.drawCircle(Offset(cx + offset, cy), r, paintB);
    canvas.drawCircle(Offset(cx + offset, cy), r, stroke);

    // Labels
    _drawText(canvas, labelA, Offset(cx - offset - r / 2, cy - r - 14),
        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue.shade700));
    _drawText(canvas, labelB, Offset(cx + offset - r / 4, cy - r - 14),
        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red.shade700));

    // Values
    _drawText(canvas, _fmt(onlyA), Offset(cx - offset - r * 0.4, cy - 6),
        style: const TextStyle(fontSize: 14, color: Colors.black));
    _drawText(canvas, _fmt(both), Offset(cx - 8, cy - 6),
        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black));
    _drawText(canvas, _fmt(onlyB), Offset(cx + offset + r * 0.2, cy - 6),
        style: const TextStyle(fontSize: 14, color: Colors.black));

    if (neither != null) {
      _drawText(canvas, 'Neither: ${_fmt(neither)}', Offset(pad, size.height - pad - 16),
          style: TextStyle(color: Colors.grey.shade700, fontSize: 12));
    }
  }

  @override
  bool shouldRepaint(covariant TwoSetOverlapPainter old) => true;
}

// ═══════════════════════════════════════════════════════════════════
//  GENERIC FALLBACK PAINTER (for unknown types)
// ═══════════════════════════════════════════════════════════════════
class GenericDiagramPainter extends CustomPainter {
  final Map<String, dynamic> spec;
  GenericDiagramPainter({required this.spec});

  @override
  void paint(Canvas canvas, Size size) {
    _drawText(canvas, 'Diagram: ${spec["type"] ?? "unknown"}', Offset(16, 16),
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black));
    _drawText(canvas, 'No specialized renderer for this type yet.', Offset(16, 38));
  }

  @override
  bool shouldRepaint(covariant GenericDiagramPainter old) => true;
}

/// Returns the appropriate painter for a given diagram spec.
CustomPainter? getPainterForSpec(Map<String, dynamic>? spec) {
  if (spec == null) return null;
  switch (spec['type']) {
    case 'before_after':
      return null; // handled by existing BeforeAfterPainter in main.dart
    case 'fractions_whole':
      return FractionsWholePainter(spec: spec);
    case 'difference_more_less':
      return DifferencePainter(spec: spec);
    case 'multiple_times_as_many':
      return MultiplePainter(spec: spec);
    case 'ratio':
      return RatioPainter(spec: spec);
    case 'equal_share_excess_shortage':
      return EqualSharePainter(spec: spec);
    case 'grouping_remainder':
      return GroupingPainter(spec: spec);
    case 'price_quantity':
      return PriceQtyPainter(spec: spec);
    case 'coins_notes':
      return CoinsNotesPainter(spec: spec);
    case 'speed_distance_time':
      return SDTPainter(spec: spec);
    case 'work_rate':
      return WorkRatePainter(spec: spec);
    case 'age':
      return AgePainter(spec: spec);
    case 'percentage_change':
      return PercentagePainter(spec: spec);
    case 'area_perimeter':
      return AreaPerimeterPainter(spec: spec);
    case 'two_set_overlap':
      return TwoSetOverlapPainter(spec: spec);
    default:
      return GenericDiagramPainter(spec: spec);
  }
}
