import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../widgets/glass_panel.dart';

class TeamArchitectureScreen extends StatefulWidget {
  const TeamArchitectureScreen({super.key});

  @override
  State<TeamArchitectureScreen> createState() => _TeamArchitectureScreenState();
}

class _TeamArchitectureScreenState extends State<TeamArchitectureScreen> {
  List<MemberRole> _roles = [];
  Map<String, dynamic> _health = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final roles = await ApiService().fetchTeamRoles();
    final health = await ApiService().checkHealth();
    if (mounted) {
      setState(() {
        _roles = roles;
        _health = health;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.cyan));
    }

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
                    '6-Member Team Delegation & Architecture Topology',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Engineered for Hack With Hyderabad 3.0 / Devnovate Hackathon',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                  ),
                ],
              ),
              Row(
                children: [
                  _healthBadge('API', _health['status'] ?? 'healthy'),
                  const SizedBox(width: 8),
                  _healthBadge('PostgreSQL', _health['postgres'] ?? 'standby'),
                  const SizedBox(width: 8),
                  _healthBadge('Redis', _health['redis'] ?? 'standby'),
                ],
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Team Member Grid
          LayoutBuilder(
            builder: (context, constraints) {
              final isNarrow = constraints.maxWidth < 950;
              final crossAxisCount = isNarrow ? 1 : 2;

              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _roles.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: crossAxisCount,
                  mainAxisExtent: 220,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                ),
                itemBuilder: (context, index) {
                  return _buildMemberCard(_roles[index]);
                },
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _healthBadge(String name, String status) {
    final isOnline = status == 'healthy' || status == 'standby';
    final Color color = isOnline ? AppTheme.emerald : AppTheme.rose;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(radius: 3, backgroundColor: color),
          const SizedBox(width: 5),
          Text(
            '$name: $status'.toUpperCase(),
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: color, fontFamily: 'monospace'),
          ),
        ],
      ),
    );
  }

  Widget _buildMemberCard(MemberRole role) {
    Color accentColor = AppTheme.cyan;
    if (role.number == 2) accentColor = AppTheme.indigo;
    if (role.number == 3) accentColor = AppTheme.cyan;
    if (role.number == 4) accentColor = AppTheme.purple;
    if (role.number == 5) accentColor = AppTheme.emerald;
    if (role.number == 6) accentColor = AppTheme.rose;

    return GlassPanel(
      borderColor: accentColor.withOpacity(0.3),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: accentColor.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: accentColor.withOpacity(0.5)),
                    ),
                    child: Center(
                      child: Text(
                        'M${role.number}',
                        style: TextStyle(
                          color: accentColor,
                          fontWeight: FontWeight.w900,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        role.name,
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                      ),
                      Text(
                        role.title,
                        style: TextStyle(fontSize: 11, color: accentColor, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.emerald.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  role.status,
                  style: const TextStyle(fontSize: 10, color: AppTheme.emerald, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            role.focus,
            style: const TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.3),
          ),
          const SizedBox(height: 8),
          const Divider(),
          const SizedBox(height: 6),
          Expanded(
            child: ListView(
              physics: const NeverScrollableScrollPhysics(),
              children: role.keyDeliverables.map(
                (d) => Padding(
                  padding: const EdgeInsets.only(bottom: 3),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('✓ ', style: TextStyle(color: AppTheme.emerald, fontSize: 11)),
                      Expanded(
                        child: Text(
                          d,
                          style: const TextStyle(fontSize: 10.5, color: AppTheme.textSecondary),
                        ),
                      ),
                    ],
                  ),
                ),
              ).toList(),
            ),
          ),
        ],
      ),
    );
  }
}
