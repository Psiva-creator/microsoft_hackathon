import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_panel.dart';
import '../widgets/metric_card.dart';

class OverviewScreen extends StatelessWidget {
  final Function(int) onNavigateToTab;

  const OverviewScreen({
    super.key,
    required this.onNavigateToTab,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Banner
          Wrap(
            spacing: 16,
            runSpacing: 12,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 10,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      const Text(
                        'Autonomous Incident Intelligence Platform',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          color: AppTheme.textPrimary,
                          letterSpacing: -0.5,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.emerald.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: AppTheme.emerald.withOpacity(0.4)),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircleAvatar(radius: 3, backgroundColor: AppTheme.emerald),
                            SizedBox(width: 5),
                            Text(
                              'ENGINE ONLINE',
                              style: TextStyle(
                                fontSize: 9,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.emerald,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Multi-agent cognitive architecture combining Prefrontal Working Memory, Hippocampal Retrieval & Neocortical Replay',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                  ),
                ],
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.cyan,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  elevation: 0,
                ),
                onPressed: () => onNavigateToTab(1), // Go to Live Incident
                icon: const Icon(Icons.flash_on_rounded, size: 16),
                label: const Text(
                  'Launch Live Triage',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Executive KPI Cards
          LayoutBuilder(
            builder: (context, constraints) {
              final double cardWidth = (constraints.maxWidth - 36) / 4;
              final bool isSmall = constraints.maxWidth < 900;

              if (isSmall) {
                return const Column(
                  children: [
                    MetricCard(
                      title: 'Hybrid Recall@3',
                      value: '100.0%',
                      subtitle: 'Exceeds 80% benchmark target by +20%',
                      icon: Icons.track_changes_rounded,
                      accentColor: AppTheme.emerald,
                      badge: 'WINNER',
                    ),
                    SizedBox(height: 12),
                    MetricCard(
                      title: 'p50 Latency',
                      value: '1.86 ms',
                      subtitle: '268x faster than 500ms production SLA',
                      icon: Icons.speed_rounded,
                      accentColor: AppTheme.cyan,
                      badge: 'SLA PASS',
                    ),
                    SizedBox(height: 12),
                    MetricCard(
                      title: 'Safety Guarantee',
                      value: '100%',
                      subtitle: 'Strict read-only guardrails (ALLOW_ACTIONS=false)',
                      icon: Icons.shield_rounded,
                      accentColor: AppTheme.amber,
                      badge: 'LOCKED',
                    ),
                    SizedBox(height: 12),
                    MetricCard(
                      title: 'Replay Clusters',
                      value: '8 Patterns',
                      subtitle: 'Synthesized via sleep-replay consolidation',
                      icon: Icons.psychology_rounded,
                      accentColor: AppTheme.indigo,
                    ),
                  ],
                );
              }

              return Row(
                children: [
                  SizedBox(
                    width: cardWidth,
                    child: const MetricCard(
                      title: 'Hybrid Recall@3',
                      value: '100.0%',
                      subtitle: 'Exceeds 80% benchmark target by +20%',
                      icon: Icons.track_changes_rounded,
                      accentColor: AppTheme.emerald,
                      badge: 'WINNER',
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: cardWidth,
                    child: const MetricCard(
                      title: 'p50 Latency',
                      value: '1.86 ms',
                      subtitle: '268x faster than 500ms production SLA',
                      icon: Icons.speed_rounded,
                      accentColor: AppTheme.cyan,
                      badge: 'SLA PASS',
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: cardWidth,
                    child: const MetricCard(
                      title: 'Safety Guarantee',
                      value: '100%',
                      subtitle: 'Strict read-only guardrails (ALLOW_ACTIONS=false)',
                      icon: Icons.shield_rounded,
                      accentColor: AppTheme.amber,
                      badge: 'LOCKED',
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: cardWidth,
                    child: const MetricCard(
                      title: 'Replay Clusters',
                      value: '8 Patterns',
                      subtitle: 'Synthesized via sleep-replay consolidation',
                      icon: Icons.psychology_rounded,
                      accentColor: AppTheme.indigo,
                    ),
                  ),
                ],
              );
            },
          ),

          const SizedBox(height: 24),

          // Interactive Cognitive Memory Map
          GlassPanel(
            borderColor: AppTheme.indigo.withOpacity(0.3),
            glowColor: AppTheme.indigo.withOpacity(0.06),
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 8,
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('🧠', style: TextStyle(fontSize: 20)),
                        SizedBox(width: 8),
                        Text(
                          'Brain-Inspired Cognitive Architecture',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                      ],
                    ),
                    TextButton.icon(
                      onPressed: () => onNavigateToTab(6), // Team architecture
                      icon: const Icon(Icons.arrow_forward_rounded, size: 14, color: AppTheme.cyan),
                      label: const Text(
                        'View Full Topology & 6-Member Map',
                        style: TextStyle(fontSize: 11, color: AppTheme.cyan),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final isNarrow = constraints.maxWidth < 800;
                    if (isNarrow) {
                      return Column(
                        children: [
                          _buildMemoryNode(
                            title: 'Prefrontal Cortex (Working Memory)',
                            subtitle: 'Redis 72h Sliding Window • Fast Multi-channel Alert Stream',
                            badge: 'M2',
                            color: AppTheme.cyan,
                            icon: Icons.layers_rounded,
                            onTap: () => onNavigateToTab(1),
                          ),
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 6),
                            child: Icon(Icons.arrow_downward_rounded, color: AppTheme.textMuted, size: 16),
                          ),
                          _buildMemoryNode(
                            title: 'Hippocampal Index (Episodic Retrieval)',
                            subtitle: '5-Signal Fusion (Dense, BM25, Fingerprint) • pgvector HNSW',
                            badge: 'M3',
                            color: AppTheme.indigo,
                            icon: Icons.search_rounded,
                            onTap: () => onNavigateToTab(2),
                          ),
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 6),
                            child: Icon(Icons.arrow_downward_rounded, color: AppTheme.textMuted, size: 16),
                          ),
                          _buildMemoryNode(
                            title: 'Neocortex (Semantic & Procedural)',
                            subtitle: 'Sleep-Replay Consolidation • Laplace Runbook Reinforcement',
                            badge: 'M5',
                            color: AppTheme.emerald,
                            icon: Icons.auto_graph_rounded,
                            onTap: () => onNavigateToTab(3),
                          ),
                        ],
                      );
                    }

                    return Row(
                      children: [
                        Expanded(
                          child: _buildMemoryNode(
                            title: 'Prefrontal Cortex (Working Memory)',
                            subtitle: 'Redis 72h Sliding Window • Multi-channel Ingestion',
                            badge: 'M2 Ingestion',
                            color: AppTheme.cyan,
                            icon: Icons.layers_rounded,
                            onTap: () => onNavigateToTab(1),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 8),
                          child: Icon(Icons.arrow_forward_rounded, color: AppTheme.textMuted, size: 16),
                        ),
                        Expanded(
                          child: _buildMemoryNode(
                            title: 'Hippocampal Index (Episodic Retrieval)',
                            subtitle: '5-Signal Fusion (Dense, BM25, Fingerprint)',
                            badge: 'M3 Retrieval',
                            color: AppTheme.indigo,
                            icon: Icons.search_rounded,
                            onTap: () => onNavigateToTab(2),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 8),
                          child: Icon(Icons.arrow_forward_rounded, color: AppTheme.textMuted, size: 16),
                        ),
                        Expanded(
                          child: _buildMemoryNode(
                            title: 'Neocortex (Semantic Consolidation)',
                            subtitle: 'Sleep-Replay Clustering • Laplace Runbooks',
                            badge: 'M5 Learning',
                            color: AppTheme.emerald,
                            icon: Icons.auto_graph_rounded,
                            onTap: () => onNavigateToTab(3),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Quick Action Launchers
          const Text(
            'Interactive Deep-Dive Modules',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, constraints) {
              final isNarrow = constraints.maxWidth < 800;
              if (isNarrow) {
                return Column(
                  children: [
                    _buildActionTile(
                      title: 'Proactive PR Outage Scanner',
                      description: 'Scan GitHub pull request diffs against past incident memory before code merges to production.',
                      icon: Icons.security_rounded,
                      color: AppTheme.rose,
                      btnText: 'Open PR Scanner',
                      onTap: () => onNavigateToTab(4),
                    ),
                    const SizedBox(height: 12),
                    _buildActionTile(
                      title: 'Ablation & Benchmark Hub',
                      description: 'Inspect quantitative evaluation tables, baseline comparisons, and sub-5ms latency verification.',
                      icon: Icons.analytics_rounded,
                      color: AppTheme.amber,
                      btnText: 'View Benchmarks',
                      onTap: () => onNavigateToTab(5),
                    ),
                  ],
                );
              }

              return Row(
                children: [
                  Expanded(
                    child: _buildActionTile(
                      title: 'Proactive PR Outage Scanner',
                      description: 'Scan GitHub pull request diffs against past incident memory before code merges to production.',
                      icon: Icons.security_rounded,
                      color: AppTheme.rose,
                      btnText: 'Open PR Scanner',
                      onTap: () => onNavigateToTab(4),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: _buildActionTile(
                      title: 'Ablation & Benchmark Hub',
                      description: 'Inspect quantitative evaluation tables, baseline comparisons, and sub-5ms latency verification.',
                      icon: Icons.analytics_rounded,
                      color: AppTheme.amber,
                      btnText: 'View Benchmarks',
                      onTap: () => onNavigateToTab(5),
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildMemoryNode({
    required String title,
    required String subtitle,
    required String badge,
    required Color color,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(icon, color: color, size: 18),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    badge,
                    style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: color),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              title,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 10.5, color: AppTheme.textMuted, height: 1.3),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionTile({
    required String title,
    required String description,
    required IconData icon,
    required Color color,
    required String btnText,
    required VoidCallback onTap,
  }) {
    return GlassPanel(
      borderColor: color.withOpacity(0.3),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: color, size: 16),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            description,
            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
          ),
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerRight,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: color,
                side: BorderSide(color: color.withOpacity(0.5)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
              onPressed: onTap,
              icon: const Icon(Icons.arrow_forward_rounded, size: 12),
              label: Text(btnText, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }
}
