import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'screens/overview_screen.dart';
import 'screens/incident_triage_screen.dart';
import 'screens/hippocampal_search_screen.dart';
import 'screens/patterns_runbooks_screen.dart';
import 'screens/pr_scanner_screen.dart';
import 'screens/evaluation_screen.dart';
import 'screens/team_architecture_screen.dart';

void main() {
  runApp(const IncidentBrainApp());
}

class IncidentBrainApp extends StatelessWidget {
  const IncidentBrainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Incident Response Agent with Brain-Inspired Memory',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const MainShellScreen(),
    );
  }
}

class MainShellScreen extends StatefulWidget {
  const MainShellScreen({super.key});

  @override
  State<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends State<MainShellScreen> {
  int _selectedTabIndex = 0;

  final List<String> _tabTitles = [
    'Overview & Executive KPI Hub',
    'Prefrontal Cortex • Live Incident Triage',
    'Hippocampal Retrieval & Pattern Separation',
    'Neocortex & Procedural Runbooks',
    'Proactive Code Memory • PR Risk Scanner',
    'Quantitative Evaluation & Ablation Suite',
    '6-Member Team Architecture Topology',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          // Cyberpunk Navigation Sidebar
          _buildSidebar(),

          // Main Screen Content Area
          Expanded(
            child: Column(
              children: [
                _buildTopAppBar(),
                Expanded(
                  child: IndexedStack(
                    index: _selectedTabIndex,
                    children: [
                      OverviewScreen(onNavigateToTab: _onSelectTab),
                      const IncidentTriageScreen(),
                      const HippocampalSearchScreen(),
                      const PatternsRunbooksScreen(),
                      const PRScannerScreen(),
                      const EvaluationScreen(),
                      const TeamArchitectureScreen(),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTopAppBar() {
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(
          bottom: BorderSide(color: AppTheme.surfaceBorder, width: 1),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              _tabTitles[_selectedTabIndex],
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Production SLA Indicator
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.emerald.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppTheme.emerald.withOpacity(0.3)),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircleAvatar(radius: 3, backgroundColor: AppTheme.emerald),
                    SizedBox(width: 5),
                    Text(
                      'SLA: 1.86ms',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.emerald,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Backend API URL indicator
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceLight,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppTheme.surfaceBorder),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.link_rounded, size: 12, color: AppTheme.cyan),
                    SizedBox(width: 4),
                    Text(
                      ':8000',
                      style: TextStyle(
                        fontSize: 10,
                        color: AppTheme.textSecondary,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSidebar() {
    return Container(
      width: 220,
      decoration: const BoxDecoration(
        color: Color(0xFF0B101B),
        border: Border(
          right: BorderSide(color: AppTheme.surfaceBorder, width: 1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // App Logo & Title
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppTheme.cyan, AppTheme.indigo],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(8),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.cyan.withOpacity(0.3),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text('🧠', style: TextStyle(fontSize: 16)),
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'INCIDENT BRAIN',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          color: AppTheme.textPrimary,
                          letterSpacing: 0.6,
                        ),
                      ),
                      Text(
                        'Cognitive Agent',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 9,
                          color: AppTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Navigation Links
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
              children: [
                _sidebarItem(
                  index: 0,
                  icon: Icons.dashboard_rounded,
                  label: 'Executive Hub',
                  badge: 'OVERVIEW',
                ),
                _sidebarItem(
                  index: 1,
                  icon: Icons.emergency_rounded,
                  label: 'Live Incident',
                  badge: 'M2 & M4',
                  accentColor: AppTheme.rose,
                ),
                _sidebarItem(
                  index: 2,
                  icon: Icons.search_rounded,
                  label: 'Hippocampus',
                  badge: 'M3 100%',
                  accentColor: AppTheme.cyan,
                ),
                _sidebarItem(
                  index: 3,
                  icon: Icons.auto_awesome_rounded,
                  label: 'Neocortex',
                  badge: 'M5 Replay',
                  accentColor: AppTheme.indigo,
                ),
                _sidebarItem(
                  index: 4,
                  icon: Icons.security_rounded,
                  label: 'PR Scanner',
                  badge: 'M6 Code',
                  accentColor: AppTheme.amber,
                ),
                _sidebarItem(
                  index: 5,
                  icon: Icons.analytics_rounded,
                  label: 'Benchmarks',
                  badge: 'M5 Eval',
                ),
                _sidebarItem(
                  index: 6,
                  icon: Icons.people_alt_rounded,
                  label: '6-Member Team',
                  badge: 'Devnovate',
                ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Sidebar Footer Status
          Padding(
            padding: const EdgeInsets.all(12),
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF131B2E),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.surfaceBorder),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'HACKATHON BUILD',
                    style: TextStyle(
                      fontSize: 8,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.cyan,
                      letterSpacing: 0.5,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Hack With Hyderabad 3.0',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  Text(
                    'Target UI Score: 10/10 ⭐',
                    style: TextStyle(fontSize: 9, color: AppTheme.emerald),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sidebarItem({
    required int index,
    required IconData icon,
    required String label,
    String? badge,
    Color? accentColor,
  }) {
    final isSelected = _selectedTabIndex == index;
    final color = accentColor ?? AppTheme.cyan;

    return Container(
      margin: const EdgeInsets.only(bottom: 2),
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        selected: isSelected,
        selectedTileColor: color.withOpacity(0.12),
        dense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
        leading: Icon(
          icon,
          size: 16,
          color: isSelected ? color : AppTheme.textMuted,
        ),
        title: Text(
          label,
          style: TextStyle(
            fontSize: 11.5,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? AppTheme.textPrimary : AppTheme.textSecondary,
          ),
        ),
        trailing: badge != null
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: isSelected ? color.withOpacity(0.25) : AppTheme.surfaceLight,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  badge,
                  style: TextStyle(
                    fontSize: 8.5,
                    fontWeight: FontWeight.bold,
                    color: isSelected ? color : AppTheme.textMuted,
                  ),
                ),
              )
            : null,
        onTap: () => _onSelectTab(index),
      ),
    );
  }

  void _onSelectTab(int index) {
    setState(() => _selectedTabIndex = index);
  }
}
