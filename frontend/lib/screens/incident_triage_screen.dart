import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../widgets/glass_panel.dart';
import '../widgets/slack_preview_card.dart';

class IncidentTriageScreen extends StatefulWidget {
  const IncidentTriageScreen({super.key});

  @override
  State<IncidentTriageScreen> createState() => _IncidentTriageScreenState();
}

class _IncidentTriageScreenState extends State<IncidentTriageScreen> {
  String _selectedScenario = 'A';
  bool _isLoading = false;
  Map<String, dynamic> _scenarioData = {};

  @override
  void initState() {
    super.initState();
    _loadScenario('A');
  }

  Future<void> _loadScenario(String key) async {
    setState(() {
      _selectedScenario = key;
      _isLoading = true;
    });

    final data = await ApiService().loadScenario(key);

    if (mounted) {
      setState(() {
        _scenarioData = data;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final timeline = (_scenarioData['timeline'] as List<TimelineEvent>?) ?? [];
    final hypotheses = (_scenarioData['hypotheses'] as List<Hypothesis>?) ?? [];
    final runbooks = (_scenarioData['recommended_runbooks'] as List<Runbook>?) ?? [];
    final title = _scenarioData['title'] ?? 'Incident Triage';
    final service = _scenarioData['service'] ?? 'service';
    final incidentId = _scenarioData['incident_id'] ?? 'INC-000';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header & Scenario Selector
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Prefrontal Cortex • Live Incident Command Center',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Real-time working memory event stream, ReAct reasoning & human approval guardrails',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppTheme.amber.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.amber.withOpacity(0.4)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.lock_rounded, size: 14, color: AppTheme.amber),
                    SizedBox(width: 6),
                    Text(
                      'SAFETY GUARD: ALLOW_ACTIONS=FALSE',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.amber,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Scenario Preset Switcher
          GlassPanel(
            padding: const EdgeInsets.all(16),
            borderColor: AppTheme.cyan.withOpacity(0.3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.play_circle_filled_rounded, color: AppTheme.cyan, size: 16),
                    SizedBox(width: 8),
                    Text(
                      'Execute Real Outage Scenario Benchmark:',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final isNarrow = constraints.maxWidth < 750;
                    return Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: [
                        _scenarioButton(
                          id: 'A',
                          title: 'Scenario A: DB Pool Leak',
                          subtitle: 'checkout-api • 503 saturation',
                          color: AppTheme.cyan,
                          isNarrow: isNarrow,
                        ),
                        _scenarioButton(
                          id: 'B',
                          title: 'Scenario B: Cert Expiry',
                          subtitle: 'auth-gateway • TLS handshake',
                          color: AppTheme.rose,
                          isNarrow: isNarrow,
                        ),
                        _scenarioButton(
                          id: 'C',
                          title: 'Scenario C: Novel Queue Lag',
                          subtitle: 'order-worker • OOM exit 137',
                          color: AppTheme.amber,
                          isNarrow: isNarrow,
                        ),
                        _scenarioButton(
                          id: 'D',
                          title: 'Scenario D: DNS Look-Alike',
                          subtitle: 'CoreDNS • Disambiguation',
                          color: AppTheme.indigo,
                          isNarrow: isNarrow,
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(color: AppTheme.cyan),
              ),
            )
          else
            LayoutBuilder(
              builder: (context, constraints) {
                final isStacked = constraints.maxWidth < 1000;

                final leftColumn = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Incident Details Card
                    GlassPanel(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.rose.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppTheme.rose.withOpacity(0.5)),
                                ),
                                child: const Text(
                                  'P1 CRITICAL',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.rose,
                                    fontFamily: 'monospace',
                                  ),
                                ),
                              ),
                              Text(
                                incidentId,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: AppTheme.cyan,
                                  fontWeight: FontWeight.bold,
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            title,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(Icons.dns_rounded, size: 13, color: AppTheme.textMuted),
                              const SizedBox(width: 5),
                              Text(
                                'Service: $service',
                                style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, fontFamily: 'monospace'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 18),

                    // Prefrontal Cortex Event Stream
                    GlassPanel(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                'Prefrontal Working Memory Timeline',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              Text(
                                '${timeline.length} Ingested Events',
                                style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          ...timeline.map((event) => _buildTimelineTile(event)),
                        ],
                      ),
                    ),
                  ],
                );

                final rightColumn = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Ranked Hypotheses
                    GlassPanel(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Ranked Hypotheses (Member 4 Agent)',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              Text('ReAct Loop', style: TextStyle(fontSize: 11, color: AppTheme.cyan)),
                            ],
                          ),
                          const SizedBox(height: 14),
                          ...hypotheses.map((h) => _buildHypothesisCard(h)),
                        ],
                      ),
                    ),

                    const SizedBox(height: 18),

                    // Slack Block Kit Preview
                    SlackPreviewCard(
                      incidentId: incidentId,
                      title: title,
                      service: service,
                      hypotheses: hypotheses,
                      runbooks: runbooks,
                    ),
                  ],
                );

                if (isStacked) {
                  return Column(
                    children: [
                      leftColumn,
                      const SizedBox(height: 20),
                      rightColumn,
                    ],
                  );
                }

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 5, child: leftColumn),
                    const SizedBox(width: 20),
                    Expanded(flex: 6, child: rightColumn),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _scenarioButton({
    required String id,
    required String title,
    required String subtitle,
    required Color color,
    required bool isNarrow,
  }) {
    final isSelected = _selectedScenario == id;
    return InkWell(
      onTap: () => _loadScenario(id),
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? color.withOpacity(0.2) : const Color(0xFF131B2E),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? color : AppTheme.surfaceBorder,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: isSelected ? color : AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 10, color: AppTheme.textMuted),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineTile(TimelineEvent event) {
    Color badgeColor = AppTheme.cyan;
    IconData icon = Icons.info_outline;

    switch (event.kind) {
      case 'alert':
        badgeColor = AppTheme.rose;
        icon = Icons.warning_rounded;
        break;
      case 'log':
        badgeColor = AppTheme.amber;
        icon = Icons.receipt_long_rounded;
        break;
      case 'metric':
        badgeColor = AppTheme.indigo;
        icon = Icons.show_chart_rounded;
        break;
      case 'action':
        badgeColor = AppTheme.emerald;
        icon = Icons.shield_rounded;
        break;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: badgeColor.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 14, color: badgeColor),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      event.source,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: badgeColor,
                      ),
                    ),
                    Text(
                      event.ts,
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppTheme.textMuted,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  event.text,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.textSecondary,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHypothesisCard(Hypothesis h) {
    final isConfirmed = h.status == 'confirmed';
    final Color badgeColor = isConfirmed ? AppTheme.emerald : AppTheme.textMuted;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isConfirmed ? AppTheme.emerald.withOpacity(0.4) : AppTheme.surfaceBorder,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                h.id,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.cyan,
                  fontFamily: 'monospace',
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '${(h.confidence * 100).toInt()}% Confidence',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: badgeColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            h.description,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
              height: 1.3,
            ),
          ),
          if (h.evidence.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...h.evidence.map(
              (e) => Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• ', style: TextStyle(color: AppTheme.cyan, fontSize: 11)),
                    Expanded(
                      child: Text(
                        e,
                        style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
