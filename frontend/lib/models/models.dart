class Incident {
  final String id;
  final String title;
  final List<String> services;
  final String status;
  final String severity;
  final String timestamp;
  final String? summary;

  Incident({
    required this.id,
    required this.title,
    required this.services,
    this.status = 'active',
    this.severity = 'P1',
    required this.timestamp,
    this.summary,
  });

  factory Incident.fromJson(Map<String, dynamic> json) {
    return Incident(
      id: json['id'] ?? json['live_incident_id'] ?? 'INC-UNKNOWN',
      title: json['title'] ?? 'Untitled Incident',
      services: List<String>.from(json['services'] ?? ['unknown']),
      status: json['status'] ?? 'active',
      severity: json['severity'] ?? 'P1',
      timestamp: json['timestamp'] ?? json['ts'] ?? DateTime.now().toIso8601String(),
      summary: json['summary'],
    );
  }
}

class TimelineEvent {
  final String ts;
  final String kind; // alert, log, metric, note, action
  final String source;
  final String text;
  final Map<String, dynamic>? data;

  TimelineEvent({
    required this.ts,
    required this.kind,
    required this.source,
    required this.text,
    this.data,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) {
    return TimelineEvent(
      ts: json['ts'] ?? '',
      kind: json['kind'] ?? 'log',
      source: json['source'] ?? 'system',
      text: json['text'] ?? '',
      data: json['data'] != null ? Map<String, dynamic>.from(json['data']) : null,
    );
  }
}

class Hypothesis {
  final String id;
  final String description;
  final double confidence;
  final List<String> evidence;
  final bool requiresApproval;
  final String status; // active, confirmed, refuted

  Hypothesis({
    required this.id,
    required this.description,
    required this.confidence,
    required this.evidence,
    this.requiresApproval = false,
    this.status = 'active',
  });

  factory Hypothesis.fromJson(Map<String, dynamic> json) {
    return Hypothesis(
      id: json['id'] ?? 'H-01',
      description: json['description'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      evidence: List<String>.from(json['evidence'] ?? []),
      requiresApproval: json['requires_human_approval'] ?? false,
      status: json['status'] ?? 'active',
    );
  }
}

class ScoredIncident {
  final String id;
  final String title;
  final double score;
  final List<String> services;
  final String rootCause;
  final List<String> runbookIds;
  final Map<String, double> signalBreakdown;
  final List<String> separationFlags;

  ScoredIncident({
    required this.id,
    required this.title,
    required this.score,
    required this.services,
    required this.rootCause,
    required this.runbookIds,
    required this.signalBreakdown,
    this.separationFlags = const [],
  });

  factory ScoredIncident.fromJson(Map<String, dynamic> json) {
    final breakdownRaw = json['relevance_breakdown'] as Map<String, dynamic>? ?? {};
    final Map<String, double> breakdown = {};
    breakdownRaw.forEach((k, v) {
      breakdown[k] = (v as num).toDouble();
    });

    return ScoredIncident(
      id: json['id'] ?? '',
      title: json['title'] ?? 'Incident',
      score: (json['score'] ?? 0.0).toDouble(),
      services: List<String>.from(json['services'] ?? []),
      rootCause: json['root_cause'] ?? 'Root cause under investigation',
      runbookIds: List<String>.from(json['runbook_ids'] ?? []),
      signalBreakdown: breakdown,
      separationFlags: List<String>.from(json['separation_flags'] ?? []),
    );
  }
}

class Runbook {
  final String id;
  final String title;
  final int successCount;
  final int failureCount;
  final double successProbability;
  final String command;
  final String category;

  Runbook({
    required this.id,
    required this.title,
    required this.successCount,
    required this.failureCount,
    required this.successProbability,
    required this.command,
    required this.category,
  });

  factory Runbook.fromJson(Map<String, dynamic> json) {
    return Runbook(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      successCount: json['success_count'] ?? 0,
      failureCount: json['failure_count'] ?? 0,
      successProbability: (json['success_probability'] ?? 0.8).toDouble(),
      command: json['command'] ?? 'kubectl rollout restart',
      category: json['category'] ?? 'Operations',
    );
  }
}

class PatternCluster {
  final String id;
  final String title;
  final String ruleText;
  final List<String> triggerSignals;
  final List<String> recommendedChecks;
  final List<String> memberIncidentIds;

  PatternCluster({
    required this.id,
    required this.title,
    required this.ruleText,
    required this.triggerSignals,
    required this.recommendedChecks,
    required this.memberIncidentIds,
  });

  factory PatternCluster.fromJson(Map<String, dynamic> json) {
    return PatternCluster(
      id: json['id'] ?? 'PAT-01',
      title: json['title'] ?? 'Consolidated Pattern',
      ruleText: json['rule_text'] ?? '',
      triggerSignals: List<String>.from(json['trigger_signals'] ?? []),
      recommendedChecks: List<String>.from(json['recommended_checks'] ?? []),
      memberIncidentIds: List<String>.from(json['member_incident_ids'] ?? []),
    );
  }
}

class PRRiskResult {
  final String riskLevel; // LOW, MEDIUM, HIGH, CRITICAL
  final double riskScore; // 0.0 - 1.0
  final List<String> modifiedFiles;
  final List<Map<String, String>> matchedIncidents;
  final List<String> warnings;
  final List<String> recommendations;

  PRRiskResult({
    required this.riskLevel,
    required this.riskScore,
    required this.modifiedFiles,
    required this.matchedIncidents,
    required this.warnings,
    required this.recommendations,
  });
}

class BenchmarkResult {
  final String mode;
  final String label;
  final double recallAt1;
  final double recallAt3;
  final double recallAt5;
  final double mrr;
  final double p50LatencyMs;
  final bool isWinner;

  BenchmarkResult({
    required this.mode,
    required this.label,
    required this.recallAt1,
    required this.recallAt3,
    required this.recallAt5,
    required this.mrr,
    required this.p50LatencyMs,
    this.isWinner = false,
  });
}

class MemberRole {
  final int number;
  final String name;
  final String title;
  final String focus;
  final List<String> keyDeliverables;
  final String status;

  MemberRole({
    required this.number,
    required this.name,
    required this.title,
    required this.focus,
    required this.keyDeliverables,
    this.status = '100% Complete',
  });
}
