import 'dart:io';

import 'package:guandan_bot/guandan_bot.dart';
import 'package:logging/logging.dart';
import 'package:yaml/yaml.dart';

Future<void> main() async {
  Logger.root.level = Level.ALL;
  Logger.root.onRecord.listen((record) {
    stdout.writeln(
      '${record.time.toUtc().toIso8601String()} '
      '${record.level.name} ${record.loggerName}: ${record.message}',
    );
    if (record.error != null) {
      stdout.writeln('  error: ${record.error}');
    }
    if (record.stackTrace != null) {
      stdout.writeln('  stack: ${record.stackTrace}');
    }
  });

  final config = _loadConfig();

  stdout.writeln('--- WebSocket Bot Configuration ---');
  stdout.writeln('  Game Server URL:  ${config.gameServerUrl}');
  stdout.writeln(
    '  Deployment Key:   ${config.deploymentKey.isNotEmpty ? "(set)" : "(not set)"}',
  );
  stdout.writeln('---');

  final bot = WebSocketTestBot(
    gameServerUrl: config.gameServerUrl,
    apiKey: config.deploymentKey,
  );

  stdout.writeln('WebSocketTestBot connecting to ${config.gameServerUrl}...');
  await bot.connect();
  stdout.writeln('WebSocketTestBot connected to ${config.gameServerUrl}.');

  ProcessSignal.sigint.watch().listen((_) async {
    await bot.dispose();
    exit(0);
  });
}

/// Resolves a value from env → config.yaml → console prompt.
String? _envStr(String name) {
  final v = Platform.environment[name]?.trim();
  return (v == null || v.isEmpty) ? null : v;
}

Map<String, dynamic>? _loadYamlDoc() {
  final paths = ['config/config.yaml', '../config/config.yaml'];
  for (final path in paths) {
    final file = File(path);
    if (!file.existsSync()) continue;
    try {
      final raw = loadYaml(file.readAsStringSync());
      if (raw is Map) return Map<String, dynamic>.from(raw);
    } catch (_) {}
  }
  return null;
}

String? _prompt(String label, {String? defaultValue}) {
  final prompt = defaultValue != null
      ? '$label (default: $defaultValue): '
      : '$label: ';
  stdout.write(prompt);
  final input = stdin.readLineSync()?.trim() ?? '';
  if (input.isEmpty && defaultValue != null) {
    stdout.writeln('  → using default: $defaultValue');
    return defaultValue;
  }
  if (input.isEmpty) return null;
  return input;
}

({String gameServerUrl, String deploymentKey}) _loadConfig() {
  final yaml = _loadYamlDoc();

  // ---- Game server URL ----
  String? gameServerUrl = _envStr('GAME_SERVER_URL');
  if (gameServerUrl == null) {
    final yamlVal = yaml?['websocket_bot']?['game_server_url'];
    if (yamlVal is String && yamlVal.isNotEmpty) {
      gameServerUrl = yamlVal;
    }
  }
  gameServerUrl ??= _prompt(
    'Game Server URL',
    defaultValue: 'ws://127.0.0.1:9001',
  )!;

  // ---- Deployment key ----
  String? deploymentKey = _envStr('WEBSOCKET_BOT_DEPLOYMENT_KEY');
  if (deploymentKey == null) {
    final yamlVal = yaml?['websocket_bot']?['deployment_key'];
    if (yamlVal is String && yamlVal.isNotEmpty) {
      deploymentKey = yamlVal;
    }
  }
  deploymentKey ??= _prompt('WebSocket Bot Deployment Key') ?? '';

  return (
    gameServerUrl: gameServerUrl,
    deploymentKey: deploymentKey,
  );
}
