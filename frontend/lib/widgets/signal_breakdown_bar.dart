import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class SignalBreakdownBar extends StatelessWidget {
  final Map<String, double> breakdown;
  final double totalScore;

  const SignalBreakdownBar({
    super.key,
    required this.breakdown,
    required this.totalScore,
  });

  @override
  Widget build(BuildContext context) {
    final vector = breakdown['vector'] ?? 0.0;
    final fts = breakdown['fts'] ?? 0.0;
    final fp = breakdown['fingerprint'] ?? 0.0;
    final svc = breakdown['service'] ?? 0.0;
    final code = breakdown['code'] ?? 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              '5-Signal Hippocampal Fusion Breakdown',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppTheme.textSecondary,
              ),
            ),
            Text(
              'Total Score: ${(totalScore * 100).toStringAsFixed(1)}%',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: AppTheme.cyan,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: SizedBox(
            height: 12,
            child: Row(
              children: [
                if (vector > 0)
                  Expanded(
                    flex: (vector * 1000).toInt(),
                    child: Container(color: AppTheme.cyan),
                  ),
                if (fts > 0)
                  Expanded(
                    flex: (fts * 1000).toInt(),
                    child: Container(color: AppTheme.indigo),
                  ),
                if (fp > 0)
                  Expanded(
                    flex: (fp * 1000).toInt(),
                    child: Container(color: AppTheme.emerald),
                  ),
                if (svc > 0)
                  Expanded(
                    flex: (svc * 1000).toInt(),
                    child: Container(color: AppTheme.amber),
                  ),
                if (code > 0)
                  Expanded(
                    flex: (code * 1000).toInt(),
                    child: Container(color: AppTheme.purple),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 12,
          runSpacing: 6,
          children: [
            _legendItem('Dense Vector (0.45)', vector, AppTheme.cyan),
            _legendItem('Full-Text BM25 (0.20)', fts, AppTheme.indigo),
            _legendItem('Stack Fingerprint (0.20)', fp, AppTheme.emerald),
            _legendItem('Service Topology (0.10)', svc, AppTheme.amber),
            _legendItem('Code Jaccard (0.05)', code, AppTheme.purple),
          ],
        ),
      ],
    );
  }

  Widget _legendItem(String label, double value, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 5),
        Text(
          '$label: ${(value * 100).toStringAsFixed(1)}%',
          style: const TextStyle(
            fontSize: 10,
            color: AppTheme.textMuted,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}
