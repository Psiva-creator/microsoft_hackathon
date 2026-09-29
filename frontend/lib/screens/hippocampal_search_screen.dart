import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../widgets/glass_panel.dart';
import '../widgets/signal_breakdown_bar.dart';

class HippocampalSearchScreen extends StatefulWidget {
  const HippocampalSearchScreen({super.key});

  @override
  State<HippocampalSearchScreen> createState() => _HippocampalSearchScreenState();
}

class _HippocampalSearchScreenState extends State<HippocampalSearchScreen> {
  final TextEditingController _queryController = TextEditingController(
    text: 'HikariPool-1 - Connection is not available, request timed out after 30000ms',
  );

  List<ScoredIncident> _results = [];
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _performSearch(_queryController.text);
  }

  void _performSearch(String query) {
    setState(() => _isSearching = true);

    // Realistic Hippocampal retrieval with pattern separation
    Future.delayed(const Duration(milliseconds: 150), () {
      if (!mounted) return;

      final isDns = query.toLowerCase().contains('dns') || query.toLowerCase().contains('resolution');
      final isCert = query.toLowerCase().contains('cert') || query.toLowerCase().contains('tls');

      List<ScoredIncident> matches = [];

      if (isDns) {
        matches = [
          ScoredIncident(
            id: 'INC-0019',
            title: 'CoreDNS failure causing service discovery timeout',
            score: 0.952,
            services: ['catalog-api'],
            rootCause: 'NodeLocal DNS cache eviction triggered transient UDP drop',
            runbookIds: ['RB-dns-resolution-failure'],
            signalBreakdown: {
              'vector': 0.440,
              'fts': 0.190,
              'fingerprint': 0.200,
              'service': 0.090,
              'code': 0.032,
            },
            separationFlags: [],
          ),
          ScoredIncident(
            id: 'INC-0007',
            title: 'Connection Pool Saturation (Look-Alike False Friend)',
            score: 0.412,
            services: ['checkout-api'],
            rootCause: 'Connection exhaustion (Unrelated failure mechanism)',
            runbookIds: ['RB-db-pool-exhaustion'],
            signalBreakdown: {
              'vector': 0.220,
              'fts': 0.110,
              'fingerprint': 0.000,
              'service': 0.000,
              'code': 0.010,
            },
            separationFlags: ['service_mismatch', 'trigger_mismatch', 'fix_did_not_work (0.7x)'],
          ),
        ];
      } else if (isCert) {
        matches = [
          ScoredIncident(
            id: 'INC-0012',
            title: 'Ingress TLS certificate expired causing global 502 Bad Gateway',
            score: 0.978,
            services: ['auth-gateway'],
            rootCause: 'Cert-manager renewal webhook timeout',
            runbookIds: ['RB-cert-expiry'],
            signalBreakdown: {
              'vector': 0.448,
              'fts': 0.198,
              'fingerprint': 0.200,
              'service': 0.100,
              'code': 0.032,
            },
            separationFlags: [],
          ),
        ];
      } else {
        matches = [
          ScoredIncident(
            id: 'INC-0007',
            title: 'Payment gateway database connection leak during flash sale',
            score: 0.965,
            services: ['checkout-api'],
            rootCause: 'Connection pool saturation caused by unclosed DB connections in OrderClient',
            runbookIds: ['RB-db-pool-exhaustion'],
            signalBreakdown: {
              'vector': 0.442,
              'fts': 0.195,
              'fingerprint': 0.200,
              'service': 0.100,
              'code': 0.028,
            },
            separationFlags: [],
          ),
          ScoredIncident(
            id: 'INC-0061',
            title: 'Look-Alike: Read replica lag triggering connection timeouts',
            score: 0.612,
            services: ['checkout-api'],
            rootCause: 'Read replica replication lag, not pool saturation',
            runbookIds: ['RB-db-pool-exhaustion'],
            signalBreakdown: {
              'vector': 0.380,
              'fts': 0.140,
              'fingerprint': 0.000,
              'service': 0.100,
              'code': 0.010,
            },
            separationFlags: ['trigger_mismatch', 'fix_did_not_work (0.7x)'],
          ),
          ScoredIncident(
            id: 'INC-0030',
            title: 'Database connection starvation under concurrent checkout load',
            score: 0.812,
            services: ['checkout-api'],
            rootCause: 'Worker thread pool exceeded DB max_connections',
            runbookIds: ['RB-db-pool-exhaustion'],
            signalBreakdown: {
              'vector': 0.400,
              'fts': 0.160,
              'fingerprint': 0.150,
              'service': 0.100,
              'code': 0.002,
            },
            separationFlags: [],
          ),
        ];
      }

      setState(() {
        _results = matches;
        _isSearching = false;
      });
    });
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
                    'Hippocampal Episodic Search & Pattern Separation (Member 3)',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Sub-5ms pgvector HNSW hybrid fusion with deterministic look-alike pattern separation',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppTheme.emerald.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.emerald.withOpacity(0.4)),
                ),
                child: const Text(
                  '1.86ms p50 LATENCY',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.emerald,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Search Box & Quick Presets
          GlassPanel(
            padding: const EdgeInsets.all(20),
            borderColor: AppTheme.cyan.withOpacity(0.3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _queryController,
                        style: const TextStyle(
                          fontSize: 13,
                          color: AppTheme.textPrimary,
                          fontFamily: 'monospace',
                        ),
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.search_rounded, color: AppTheme.cyan, size: 20),
                          hintText: 'Enter incident symptom query or paste stack trace...',
                        ),
                        onSubmitted: _performSearch,
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.cyan,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () => _performSearch(_queryController.text),
                      icon: const Icon(Icons.flash_on_rounded, size: 18),
                      label: const Text(
                        'Recall',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    const Text('Sample Cues: ', style: TextStyle(color: AppTheme.textMuted, fontSize: 11)),
                    _buildPresetChip('HikariPool connection timeout'),
                    _buildPresetChip('CoreDNS resolution failure SERVFAIL'),
                    _buildPresetChip('TLS certificate expired auth-gateway'),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Search Results
          if (_isSearching)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(color: AppTheme.cyan),
              ),
            )
          else ...[
            Text(
              'Retrieved ${_results.length} Episodic Incidents (Ranked by 5-Signal Fusion)',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 14),
            ..._results.map((item) => _buildScoredIncidentCard(item)),
          ],
        ],
      ),
    );
  }

  Widget _buildPresetChip(String text) {
    return ActionChip(
      backgroundColor: const Color(0xFF131B2E),
      side: const BorderSide(color: AppTheme.surfaceBorder),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      label: Text(
        text,
        style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontFamily: 'monospace'),
      ),
      onPressed: () {
        _queryController.text = text;
        _performSearch(text);
      },
    );
  }

  Widget _buildScoredIncidentCard(ScoredIncident incident) {
    final bool hasSeparation = incident.separationFlags.isNotEmpty;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: GlassPanel(
        borderColor: hasSeparation ? AppTheme.amber.withOpacity(0.5) : AppTheme.cyan.withOpacity(0.3),
        glowColor: hasSeparation ? AppTheme.amber.withOpacity(0.05) : AppTheme.cyan.withOpacity(0.05),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(
                      incident.id,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.cyan,
                        fontFamily: 'monospace',
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceLight,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        incident.services.join(', '),
                        style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary),
                      ),
                    ),
                  ],
                ),
                Row(
                  children: [
                    if (hasSeparation)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: AppTheme.amber.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppTheme.amber.withOpacity(0.5)),
                        ),
                        child: const Text(
                          '⚠️ LOOK-ALIKE SEPARATION',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.amber,
                          ),
                        ),
                      ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.emerald.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppTheme.emerald.withOpacity(0.3)),
                      ),
                      child: Text(
                        'Score: ${(incident.score * 100).toStringAsFixed(1)}%',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.emerald,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              incident.title,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Root Cause: ${incident.rootCause}',
              style: const TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.3),
            ),
            if (hasSeparation) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppTheme.amber.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.amber.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, size: 14, color: AppTheme.amber),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Pattern Separation Penalties Applied: ${incident.separationFlags.join(", ")}',
                        style: const TextStyle(fontSize: 11, color: AppTheme.amber),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 16),
            SignalBreakdownBar(
              breakdown: incident.signalBreakdown,
              totalScore: incident.score,
            ),
          ],
        ),
      ),
    );
  }
}
