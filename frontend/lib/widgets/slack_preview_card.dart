import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';

class SlackPreviewCard extends StatefulWidget {
  final String incidentId;
  final String title;
  final String service;
  final List<Hypothesis> hypotheses;
  final List<Runbook> runbooks;

  const SlackPreviewCard({
    super.key,
    required this.incidentId,
    required this.title,
    required this.service,
    required this.hypotheses,
    required this.runbooks,
  });

  @override
  State<SlackPreviewCard> createState() => _SlackPreviewCardState();
}

class _SlackPreviewCardState extends State<SlackPreviewCard> {
  String? _feedbackState; // 'helpful', 'not_helpful'
  bool _actionApproved = false;

  @override
  Widget build(BuildContext context) {
    final topHypothesis = widget.hypotheses.isNotEmpty ? widget.hypotheses.first : null;
    final topRunbook = widget.runbooks.isNotEmpty ? widget.runbooks.first : null;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1A1D21), // Slack Dark Mode BG
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF383F45)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.5),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Slack Message Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: AppTheme.cyan.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.cyan.withOpacity(0.5)),
                  ),
                  child: const Center(
                    child: Text('🧠', style: TextStyle(fontSize: 20)),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'Incident Brain Agent',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                            decoration: BoxDecoration(
                              color: const Color(0xFF2C3136),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'APP',
                              style: TextStyle(
                                color: Color(0xFF9BA2AA),
                                fontSize: 9,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            '14:02',
                            style: TextStyle(color: Color(0xFF6B7278), fontSize: 11),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '🚨 INCIDENT DETECTED: [${widget.service.toUpperCase()}] ${widget.title}',
                        style: const TextStyle(
                          color: Color(0xFFF2C744),
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Slack Attachment Border Box
          Container(
            margin: const EdgeInsets.only(left: 56, right: 16, bottom: 16),
            decoration: const BoxDecoration(
              border: Border(
                left: BorderSide(color: Color(0xFFE01E5A), width: 4), // Slack red alert bar
              ),
            ),
            padding: const EdgeInsets.only(left: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Hypothesis Block
                if (topHypothesis != null) ...[
                  Row(
                    children: [
                      const Text(
                        '🔍 Top Ranked Hypothesis:',
                        style: TextStyle(
                          color: Color(0xFFD1D2D3),
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.emerald.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppTheme.emerald.withOpacity(0.4)),
                        ),
                        child: Text(
                          '${(topHypothesis.confidence * 100).toInt()}% Confidence',
                          style: const TextStyle(
                            color: AppTheme.emerald,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    topHypothesis.description,
                    style: const TextStyle(
                      color: Color(0xFFABAEB2),
                      fontSize: 12,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF131517),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: topHypothesis.evidence
                          .map(
                            (e) => Padding(
                              padding: const EdgeInsets.only(bottom: 2),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('• ', style: TextStyle(color: AppTheme.cyan, fontSize: 11)),
                                  Expanded(
                                    child: Text(
                                      e,
                                      style: const TextStyle(color: Color(0xFF868B90), fontSize: 11),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ],

                const SizedBox(height: 12),

                // Recommended Procedural Runbook
                if (topRunbook != null) ...[
                  Row(
                    children: [
                      const Text(
                        '🛠️ Recommended Procedural Runbook:',
                        style: TextStyle(
                          color: Color(0xFFD1D2D3),
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        'Laplace Success: ${(topRunbook.successProbability * 100).toStringAsFixed(1)}%',
                        style: const TextStyle(
                          color: AppTheme.amber,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F1113),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF2C3136)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${topRunbook.id}: ${topRunbook.title}',
                          style: const TextStyle(
                            color: AppTheme.cyan,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '\$ ${topRunbook.command}',
                          style: const TextStyle(
                            color: Color(0xFFE2E8F0),
                            fontSize: 11,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 14),

                // Slack Action Buttons
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _actionApproved
                            ? AppTheme.emerald.withOpacity(0.3)
                            : const Color(0xFF007A5A), // Slack Green
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(6),
                        ),
                      ),
                      onPressed: () {
                        setState(() {
                          _actionApproved = true;
                        });
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('✓ Human approval recorded: Runbook execution approved safely.'),
                            backgroundColor: AppTheme.emerald,
                          ),
                        );
                      },
                      icon: Icon(
                        _actionApproved ? Icons.check_circle : Icons.play_arrow_rounded,
                        size: 16,
                      ),
                      label: Text(
                        _actionApproved ? 'Execution Approved' : 'Execute Runbook',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFFD1D2D3),
                        side: const BorderSide(color: Color(0xFF565856)),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(6),
                        ),
                      ),
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Triage ticket escalated to Senior SRE On-Call Lead.')),
                        );
                      },
                      child: const Text('Escalate to Lead', style: TextStyle(fontSize: 12)),
                    ),
                  ],
                ),

                const SizedBox(height: 12),
                const Divider(color: Color(0xFF2C3136)),
                const SizedBox(height: 6),

                // Reinforcement Learning Feedback Buttons
                Row(
                  children: [
                    const Text(
                      'Was this recommendation helpful? ',
                      style: TextStyle(color: Color(0xFF868B90), fontSize: 11),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: Icon(
                        Icons.thumb_up_rounded,
                        size: 15,
                        color: _feedbackState == 'helpful' ? AppTheme.emerald : const Color(0xFF868B90),
                      ),
                      visualDensity: VisualDensity.compact,
                      onPressed: () {
                        setState(() => _feedbackState = 'helpful');
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('👍 Feedback recorded: Runbook success weight increased (+1).'),
                            backgroundColor: AppTheme.emerald,
                          ),
                        );
                      },
                    ),
                    IconButton(
                      icon: Icon(
                        Icons.thumb_down_rounded,
                        size: 15,
                        color: _feedbackState == 'not_helpful' ? AppTheme.rose : const Color(0xFF868B90),
                      ),
                      visualDensity: VisualDensity.compact,
                      onPressed: () {
                        setState(() => _feedbackState = 'not_helpful');
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('👎 Feedback recorded: Runbook down-weighted for look-alike cases.'),
                            backgroundColor: AppTheme.rose,
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
