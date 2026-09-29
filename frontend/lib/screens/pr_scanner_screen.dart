import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../widgets/glass_panel.dart';

class PRScannerScreen extends StatefulWidget {
  const PRScannerScreen({super.key});

  @override
  State<PRScannerScreen> createState() => _PRScannerScreenState();
}

class _PRScannerScreenState extends State<PRScannerScreen> {
  final TextEditingController _filesController = TextEditingController(
    text: 'services/checkout/OrderClient.py',
  );

  PRRiskResult? _scanResult;
  bool _isScanning = false;

  @override
  void initState() {
    super.initState();
    _runScan();
  }

  Future<void> _runScan() async {
    setState(() => _isScanning = true);
    final files = _filesController.text
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();

    final result = await ApiService().scanPRRisk(files);
    if (mounted) {
      setState(() {
        _scanResult = result;
        _isScanning = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Proactive Code Memory: PR Outage Scanner (Member 6)',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Cross-references Pull Request file diffs against historical post-mortems to stop outages before merge',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppTheme.rose.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.rose.withOpacity(0.4)),
                ),
                child: const Text(
                  'PRE-MERGE GATE ACTIVE',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.rose,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // File Input Box
          GlassPanel(
            padding: const EdgeInsets.all(20),
            borderColor: AppTheme.rose.withOpacity(0.3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Modified Files in PR:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _filesController,
                        style: const TextStyle(
                          fontSize: 13,
                          color: AppTheme.textPrimary,
                          fontFamily: 'monospace',
                        ),
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.code_rounded, color: AppTheme.rose, size: 20),
                          hintText: 'e.g. services/checkout/OrderClient.py, services/auth/token.go',
                        ),
                        onSubmitted: (_) => _runScan(),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.rose,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: _runScan,
                      icon: const Icon(Icons.security_rounded, size: 18),
                      label: const Text(
                        'Scan Risk',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    const Text('Test Presets: ', style: TextStyle(color: AppTheme.textMuted, fontSize: 11)),
                    ActionChip(
                      backgroundColor: const Color(0xFF131B2E),
                      side: const BorderSide(color: AppTheme.surfaceBorder),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      label: const Text(
                        '⚠️ Risky: services/checkout/OrderClient.py',
                        style: TextStyle(fontSize: 11, color: AppTheme.rose, fontFamily: 'monospace'),
                      ),
                      onPressed: () {
                        _filesController.text = 'services/checkout/OrderClient.py';
                        _runScan();
                      },
                    ),
                    ActionChip(
                      backgroundColor: const Color(0xFF131B2E),
                      side: const BorderSide(color: AppTheme.surfaceBorder),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      label: const Text(
                        '✓ Safe: docs/README.md, app/config.py',
                        style: TextStyle(fontSize: 11, color: AppTheme.emerald, fontFamily: 'monospace'),
                      ),
                      onPressed: () {
                        _filesController.text = 'docs/README.md, app/config.py';
                        _runScan();
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          if (_isScanning)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(color: AppTheme.rose),
              ),
            )
          else if (_scanResult != null) ...[
            _buildScanResultSection(_scanResult!),
          ],
        ],
      ),
    );
  }

  Widget _buildScanResultSection(PRRiskResult res) {
    final isHigh = res.riskScore >= 0.5;
    final Color riskColor = isHigh ? AppTheme.rose : AppTheme.emerald;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Top Risk Summary Card
        GlassPanel(
          borderColor: riskColor.withOpacity(0.5),
          glowColor: riskColor.withOpacity(0.08),
          padding: const EdgeInsets.all(22),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: riskColor.withOpacity(0.15),
                  shape: BoxShape.circle,
                  border: Border.all(color: riskColor.withOpacity(0.4)),
                ),
                child: Icon(
                  isHigh ? Icons.warning_amber_rounded : Icons.verified_user_rounded,
                  color: riskColor,
                  size: 32,
                ),
              ),
              const SizedBox(width: 18),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          res.riskLevel,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            color: riskColor,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: riskColor.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            'RISK SCORE: ${(res.riskScore * 100).toInt()}%',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: riskColor,
                              fontFamily: 'monospace',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      isHigh
                          ? 'This pull request modifies files implicated in catastrophic historical production outages. Extra caution and human sign-off recommended.'
                          : 'Files modified in this pull request have clean operational histories with 0 correlated outages.',
                      style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary, height: 1.3),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 20),

        // Matched Incidents
        if (res.matchedIncidents.isNotEmpty) ...[
          const Text(
            'Implicated Historical Outages & Post-Mortems',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
          ),
          const SizedBox(height: 12),
          ...res.matchedIncidents.map((inc) => _buildMatchedIncidentCard(inc)),
          const SizedBox(height: 20),
        ],

        // Warnings & Recommendations
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: GlassPanel(
                padding: const EdgeInsets.all(18),
                borderColor: AppTheme.amber.withOpacity(0.3),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.warning_rounded, color: AppTheme.amber, size: 16),
                        SizedBox(width: 8),
                        Text(
                          'Pre-Merge Warnings',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...res.warnings.map(
                      (w) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(w, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: GlassPanel(
                padding: const EdgeInsets.all(18),
                borderColor: AppTheme.cyan.withOpacity(0.3),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.check_circle_outline_rounded, color: AppTheme.cyan, size: 16),
                        SizedBox(width: 8),
                        Text(
                          'Mandated Pre-Merge Actions',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...res.recommendations.map(
                      (r) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text('• $r', style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMatchedIncidentCard(Map<String, String> inc) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.rose.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                inc['id'] ?? '',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.rose,
                  fontFamily: 'monospace',
                ),
              ),
              const Text('Correlated Outage', style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            inc['title'] ?? '',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
          ),
          const SizedBox(height: 4),
          Text(
            'Root Cause: ${inc['root_cause']}',
            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
          ),
          const SizedBox(height: 4),
          Text(
            'Historical Remediation: ${inc['fix']}',
            style: const TextStyle(fontSize: 11, color: AppTheme.emerald),
          ),
        ],
      ),
    );
  }
}
