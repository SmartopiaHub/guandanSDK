import 'dart:io';

import 'package:guandan_bot/guandan_bot.dart';
import 'package:logging/logging.dart';
import 'package:yaml/yaml.dart';

/// Configuration for the HTTP test bot, resolved from env → YAML → console.
final class BotConfig {
  const BotConfig({
    required this.host,
    required this.port,
    this.deploymentKey,
    this.invocationKey,
    this.publicBaseUrl,
    this.lobbyUrl,
    this.accessToken,
    this.providerId,
    this.definitionIds = const [],
    this.protocolVersions = const ['guandan-bot-v1'],
    this.maxConcurrentSessions = 10,
    this.region,
  });

  final String host;
  final int port;

  /// Key the bot presents to the lobby / game server (bot → server).
  final String? deploymentKey;

  /// Optional key the bot checks on incoming requests (server → bot).
  final String? invocationKey;

  final String? publicBaseUrl;
  final String? lobbyUrl;
  final String? accessToken;
  final String? providerId;
  final List<String> definitionIds;
  final List<String> protocolVersions;
  final int maxConcurrentSessions;
  final String? region;
}

// =============================================================================
// Entry point
// =============================================================================

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

  final loader = BotConfigLoader();
  final config = await loader.load();

  _printConfigSummary(config);

  final bot = HttpTestBot(
    host: config.host,
    port: config.port,
    apiKey: config.invocationKey,
  );
  await bot.start();
  stdout.writeln('HttpTestBot listening at ${bot.baseUrl}');

  final publicBaseUrl =
      config.publicBaseUrl != null && config.publicBaseUrl!.isNotEmpty
          ? Uri.tryParse(config.publicBaseUrl!)
          : null;
  await _registerDeploymentIfConfigured(
    bot,
    deploymentBaseUrl: publicBaseUrl,
    config: config,
  );

  ProcessSignal.sigint.watch().listen((_) async {
    await bot.dispose();
    exit(0);
  });
}

// =============================================================================
// Config loader — env → config.yaml → console prompt
// =============================================================================

class BotConfigLoader {
  BotConfigLoader({
    Stdin? stdinIn,
    Stdout? stdoutIn,
    String? configPath,
    Map<String, String>? env,
  })  : _stdin = stdinIn ?? stdin,
        _stdout = stdoutIn ?? stdout,
        _configPath = configPath,
        _env = env ?? Platform.environment;

  final Stdin _stdin;
  final Stdout _stdout;
  final String? _configPath;
  final Map<String, String> _env;

  Map<String, dynamic>? _yamlDoc;

  /// Resolve the config file path.
  String _resolveConfigPath() {
    if (_configPath != null) return _configPath;

    // Try CWD first (most common when running from guandan_bot/)
    final cwdPath = 'config/config.yaml';
    if (File(cwdPath).existsSync()) return cwdPath;

    // Fall back to package root relative to this script
    final scriptDir = File(Platform.script.toFilePath()).parent;
    final pkgPath = '$scriptDir/../config/config.yaml';
    return pkgPath;
  }

  /// Parse the YAML config file (lazy, once).
  Map<String, dynamic>? _loadYaml() {
    if (_yamlDoc != null) return _yamlDoc;
    final path = _resolveConfigPath();
    final file = File(path);
    if (!file.existsSync()) {
      return _yamlDoc = null;
    }
    try {
      final raw = loadYaml(file.readAsStringSync());
      if (raw is Map) {
        _yamlDoc = Map<String, dynamic>.from(raw);
      } else {
        _yamlDoc = null;
      }
    } catch (_) {
      _yamlDoc = null;
    }
    return _yamlDoc;
  }

  /// Look up a value from the YAML doc at [path] segments.
  dynamic _yamlGet(List<String> path) {
    final doc = _loadYaml();
    if (doc == null) return null;
    dynamic current = doc;
    for (final segment in path) {
      if (current is Map) {
        current = current[segment];
      } else {
        return null;
      }
    }
    return current;
  }

  /// Read a string from env.
  String? _envStr(String name) {
    final v = _env[name]?.trim();
    return (v == null || v.isEmpty) ? null : v;
  }

  /// Read a list from env (comma-separated).
  List<String> _envList(String name) {
    return (_envStr(name) ?? '')
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList(growable: false);
  }

  /// Prompt the user on the console.  Returns the user's input trimmed, or
  /// [defaultValue] when the user presses Enter without typing anything.
  /// Returns null when there is no default and the user enters nothing.
  String? _prompt(String label, {String? defaultValue}) {
    final prompt =
        defaultValue != null ? '$label (default: $defaultValue): ' : '$label: ';
    _stdout.write(prompt);
    final input = _stdin.readLineSync()?.trim() ?? '';
    if (input.isEmpty && defaultValue != null) {
      _stdout.writeln('  → using default: $defaultValue');
      return defaultValue;
    }
    if (input.isEmpty) return null;
    return input;
  }

  /// Resolve a required string config value.
  /// Chain: env → yaml → console prompt (with optional default).
  String? _resolveString({
    required String envName,
    required List<String> yamlPath,
    String? promptLabel,
    String? defaultValue,
    bool required = false,
  }) {
    // 1. Environment variable
    final envVal = _envStr(envName);
    if (envVal != null) return envVal;

    // 2. config.yaml
    final yamlVal = _yamlGet(yamlPath);
    if (yamlVal is String && yamlVal.isNotEmpty) return yamlVal;

    // 3. Console prompt (always prompt for required or when default exists,
    //    to avoid silently using defaults in main)
    if (required || defaultValue != null) {
      return _prompt(promptLabel ?? envName, defaultValue: defaultValue);
    }
    return null;
  }

  /// Resolve an optional string (no prompt unless required).
  String? _resolveOptionalString({
    required String envName,
    required List<String> yamlPath,
    String? promptLabel,
    String? defaultValue,
  }) {
    final envVal = _envStr(envName);
    if (envVal != null) return envVal;

    final yamlVal = _yamlGet(yamlPath);
    if (yamlVal is String && yamlVal.isNotEmpty) return yamlVal;

    if (defaultValue != null) {
      return _prompt(promptLabel ?? envName, defaultValue: defaultValue);
    }
    return null;
  }

  /// Resolve a list config value.
  List<String> _resolveList({
    required String envName,
    required List<String> envListNames,
    required List<String> yamlPath,
    String? promptLabel,
    List<String> defaultValue = const [],
  }) {
    // 1. Environment (comma-separated list)
    final envVals = _envList(envName);
    if (envVals.isNotEmpty) return envVals;

    // Also check alternate env names
    for (final altName in envListNames) {
      final altVals = _envList(altName);
      if (altVals.isNotEmpty) return altVals;
    }

    // 2. config.yaml
    final yamlVal = _yamlGet(yamlPath);
    if (yamlVal is List && yamlVal.isNotEmpty) {
      return yamlVal
          .map((e) => e.toString().trim())
          .where((e) => e.isNotEmpty)
          .toList(growable: false);
    }

    // 3. Console prompt (always show default so user can confirm)
    final defaultStr = defaultValue.join(', ');
    final input = _prompt(
      promptLabel ?? envName,
      defaultValue: defaultStr.isNotEmpty ? defaultStr : null,
    );
    if (input == null || input.isEmpty) return defaultValue;
    return input
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList(growable: false);
  }

  /// Resolve an int config value.
  int _resolveInt({
    required String envName,
    required List<String> yamlPath,
    String? promptLabel,
    int defaultValue = 0,
  }) {
    // 1. Environment variable
    final envVal = _envStr(envName);
    if (envVal != null) {
      final parsed = int.tryParse(envVal);
      if (parsed != null) return parsed;
    }

    // 2. config.yaml
    final yamlVal = _yamlGet(yamlPath);
    if (yamlVal is int) return yamlVal;
    if (yamlVal is num) return yamlVal.toInt();

    // 3. Console prompt
    while (true) {
      final input = _prompt(
        promptLabel ?? envName,
        defaultValue: defaultValue.toString(),
      );
      if (input == null || input.isEmpty) return defaultValue;
      final parsed = int.tryParse(input);
      if (parsed != null) return parsed;
      _stdout.writeln('  Invalid integer, please try again.');
    }
  }

  /// Load the full configuration.
  Future<BotConfig> load() async {
    // ---- Network bind ----
    final host = _resolveString(
      envName: 'HTTP_BOT_HOST',
      yamlPath: ['http_bot', 'host'],
      promptLabel: 'HTTP Bot host',
      defaultValue: '127.0.0.1',
    )!;

    final port = _resolveInt(
      envName: 'HTTP_BOT_PORT',
      yamlPath: ['http_bot', 'port'],
      promptLabel: 'HTTP Bot port',
      defaultValue: 10001,
    );

    // ---- Deployment key (bot → server) ----
    final deploymentKey = _resolveString(
      envName: 'HTTP_BOT_DEPLOYMENT_KEY',
      yamlPath: ['http_bot', 'deployment_key'],
      promptLabel: 'HTTP Bot Deployment Key (bot → server)',
    );

    // ---- Invocation key (server → bot, optional) ----
    var invocationKey = _resolveString(
      envName: 'HTTP_BOT_INVOCATION_KEY',
      yamlPath: ['http_bot', 'invocation_key'],
      promptLabel: 'HTTP Bot Invocation Key (server → bot, optional)',
    );
    invocationKey ??= _envStr('HTTP_BOT_API_KEY');
    final legacyYamlApiKey = _yamlGet(['http_bot', 'api_key']);
    if (invocationKey == null &&
        legacyYamlApiKey is String &&
        legacyYamlApiKey.isNotEmpty) {
      invocationKey = legacyYamlApiKey;
    }

    // ---- Public base URL (optional) ----
    final publicBaseUrl = _resolveOptionalString(
      envName: 'HTTP_BOT_PUBLIC_BASE_URL',
      yamlPath: ['http_bot', 'public_base_url'],
      promptLabel: 'Public base URL',
    );

    // ---- Auto-registration fields (all optional) ----
    final lobbyUrl = _resolveOptionalString(
      envName: 'LOBBY_URL',
      yamlPath: ['lobby', 'url'],
      promptLabel: 'Lobby URL',
      defaultValue: 'http://127.0.0.1:8686',
    );

    // Developer access token: check LOBBY_ACCESS_TOKEN then DEVELOPER_ACCESS_TOKEN
    String? accessToken = _envStr('LOBBY_ACCESS_TOKEN');
    accessToken ??= _envStr('DEVELOPER_ACCESS_TOKEN');
    if (accessToken == null) {
      final yamlVal = _yamlGet(['lobby', 'access_token']);
      if (yamlVal is String && yamlVal.isNotEmpty) {
        accessToken = yamlVal;
      }
    }

    final providerId = _resolveOptionalString(
      envName: 'BOT_PROVIDER_ID',
      yamlPath: ['http_bot', 'provider_id'],
      promptLabel: 'Bot Provider ID',
    );

    final definitionIds = _resolveList(
      envName: 'BOT_DEFINITION_IDS',
      envListNames: ['BOT_DEFINITION_ID'],
      yamlPath: ['http_bot', 'definition_ids'],
      promptLabel: 'Bot Definition ID(s) (comma-separated)',
    );

    final protocolVersions = _resolveList(
      envName: 'BOT_PROTOCOL_VERSIONS',
      envListNames: const [],
      yamlPath: ['http_bot', 'protocol_versions'],
      promptLabel: 'Protocol versions (comma-separated)',
      defaultValue: ['guandan-bot-v1'],
    );

    final maxConcurrentSessions = _resolveInt(
      envName: 'BOT_MAX_CONCURRENT_SESSIONS',
      yamlPath: ['http_bot', 'max_concurrent_sessions'],
      promptLabel: 'Max concurrent sessions',
      defaultValue: 10,
    );

    final region = _resolveOptionalString(
      envName: 'BOT_REGION',
      yamlPath: ['http_bot', 'region'],
      promptLabel: 'Region',
    );

    return BotConfig(
      host: host,
      port: port,
      deploymentKey: deploymentKey,
      invocationKey: invocationKey,
      publicBaseUrl: publicBaseUrl,
      lobbyUrl: lobbyUrl,
      accessToken: accessToken,
      providerId: providerId,
      definitionIds: definitionIds,
      protocolVersions: protocolVersions,
      maxConcurrentSessions: maxConcurrentSessions,
      region: region,
    );
  }
}

// =============================================================================
// Config summary
// =============================================================================

void _printConfigSummary(BotConfig config) {
  stdout.writeln('--- Bot Configuration ---');
  stdout.writeln('  Host:               ${config.host}');
  stdout.writeln('  Port:               ${config.port}');
  stdout.writeln(
    '  Deployment Key:     ${config.deploymentKey != null && config.deploymentKey!.isNotEmpty ? "(set)" : "(not set)"}',
  );
  stdout.writeln(
    '  Invocation Key:     ${config.invocationKey != null && config.invocationKey!.isNotEmpty ? "(set)" : "(not set — no incoming auth)"}',
  );
  stdout.writeln(
    '  Public Base URL:    ${config.publicBaseUrl ?? "(bind address)"}',
  );
  if (config.lobbyUrl != null && config.lobbyUrl!.isNotEmpty) {
    stdout.writeln('  Lobby URL:          ${config.lobbyUrl}');
    stdout.writeln(
      '  Access Token:       ${config.accessToken != null && config.accessToken!.isNotEmpty ? "(set)" : "(not set)"}',
    );
    stdout.writeln(
      '  Provider ID:        ${config.providerId ?? "(not set)"}',
    );
    stdout.writeln(
      '  Definition IDs:     ${config.definitionIds.isEmpty ? "(not set)" : config.definitionIds.join(", ")}',
    );
  }
  stdout.writeln(
    '  Protocol Versions:  ${config.protocolVersions.join(", ")}',
  );
  stdout.writeln('  Max Sessions:       ${config.maxConcurrentSessions}');
  if (config.region != null && config.region!.isNotEmpty) {
    stdout.writeln('  Region:             ${config.region}');
  }
  stdout.writeln('---');
}

// =============================================================================
// Optional auto-registration
// =============================================================================

Future<void> _registerDeploymentIfConfigured(
  HttpTestBot bot, {
  Uri? deploymentBaseUrl,
  required BotConfig config,
}) async {
  final lobbyUrl = config.lobbyUrl;
  final accessToken = config.accessToken;
  final providerId = config.providerId;
  final definitionIds = config.definitionIds;

  final shouldRegister = lobbyUrl != null &&
      lobbyUrl.isNotEmpty &&
      accessToken != null &&
      accessToken.isNotEmpty &&
      providerId != null &&
      providerId.isNotEmpty &&
      definitionIds.isNotEmpty;

  if (!shouldRegister) {
    stdout.writeln(
      'Skipping auto-registration: missing lobby URL, access token, '
      'provider ID, or definition IDs.',
    );
    return;
  }

  final lobbyBaseUrl = Uri.parse(lobbyUrl);
  final response = await bot.registerDeployment(
    lobbyBaseUrl: lobbyBaseUrl,
    accessToken: accessToken,
    deploymentBaseUrl: deploymentBaseUrl,
    request: RegisterBotDeploymentRequest(
      providerId: providerId,
      transportType: BotTransportType.http,
      supportedBotDefinitionIds: definitionIds,
      supportedProtocolVersions: config.protocolVersions,
      maxConcurrentSessions: config.maxConcurrentSessions,
      region: config.region != null && config.region!.isNotEmpty
          ? config.region
          : null,
    ),
  );

  stdout.writeln(
    'HttpTestBot deployment registered: '
    '${response.deployment?.deploymentId ?? "(unknown deployment id)"}',
  );

  final managementKey = response.deploymentManagementKey ?? response.apiKey;
  if (managementKey != null && managementKey.isNotEmpty) {
    stdout.writeln('Deployment management key: $managementKey');
  }
  if (response.botInvocationToken != null &&
      response.botInvocationToken!.isNotEmpty) {
    stdout.writeln('Bot invocation token: ${response.botInvocationToken}');
    stdout.writeln(
      '⚠ Save this token! It is only shown once. '
      'Set it as HTTP_BOT_INVOCATION_KEY when you next start the bot.',
    );
  }
}
