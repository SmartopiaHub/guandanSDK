enum BotProviderStatus {
  pending('pending'),
  approved('approved'),
  suspended('suspended'),
  disabled('disabled');

  const BotProviderStatus(this.code);

  final String code;

  static BotProviderStatus fromCode(String code) {
    return BotProviderStatus.values.firstWhere(
      (status) => status.code == code,
      orElse: () => BotProviderStatus.pending,
    );
  }
}

enum BotVisibility {
  private('private'),
  unlisted('unlisted'),
  public('public');

  const BotVisibility(this.code);

  final String code;

  static BotVisibility fromCode(String code) {
    return BotVisibility.values.firstWhere(
      (visibility) => visibility.code == code,
      orElse: () => BotVisibility.private,
    );
  }
}

enum BotDefinitionStatus {
  draft('draft'),
  active('active'),
  deprecated('deprecated'),
  disabled('disabled');

  const BotDefinitionStatus(this.code);

  final String code;

  static BotDefinitionStatus fromCode(String code) {
    return BotDefinitionStatus.values.firstWhere(
      (status) => status.code == code,
      orElse: () => BotDefinitionStatus.draft,
    );
  }
}

enum BotTransportType {
  http('http'),
  websocket('websocket');

  const BotTransportType(this.code);

  final String code;

  static BotTransportType fromCode(String code) {
    return BotTransportType.values.firstWhere(
      (type) => type.code == code,
      orElse: () => BotTransportType.http,
    );
  }
}

enum BotDeploymentStatus {
  pendingVerification('pending_verification'),
  healthy('healthy'),
  degraded('degraded'),
  unavailable('unavailable'),
  disabled('disabled');

  const BotDeploymentStatus(this.code);

  final String code;

  static BotDeploymentStatus fromCode(String code) {
    return BotDeploymentStatus.values.firstWhere(
      (status) => status.code == code,
      orElse: () => BotDeploymentStatus.pendingVerification,
    );
  }
}

enum BotSessionStatus {
  creating('creating'),
  active('active'),
  degraded('degraded'),
  replacedByFallback('replaced_by_fallback'),
  ended('ended'),
  failed('failed');

  const BotSessionStatus(this.code);

  final String code;

  static BotSessionStatus fromCode(String code) {
    return BotSessionStatus.values.firstWhere(
      (status) => status.code == code,
      orElse: () => BotSessionStatus.creating,
    );
  }
}

class BotProvider {
  const BotProvider({
    required this.providerId,
    required this.displayName,
    required this.ownerAccountId,
    required this.contactEmail,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  final String providerId;
  final String displayName;
  final String ownerAccountId;
  final String contactEmail;
  final BotProviderStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory BotProvider.fromJson(Map<String, dynamic> json) {
    return BotProvider(
      providerId: json['provider_id'] as String,
      displayName: json['display_name'] as String,
      ownerAccountId: json['owner_account_id'] as String,
      contactEmail: json['contact_email'] as String,
      status: BotProviderStatus.fromCode(json['status'] as String? ?? ''),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'provider_id': providerId,
      'display_name': displayName,
      'owner_account_id': ownerAccountId,
      'contact_email': contactEmail,
      'status': status.code,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}

class BotDefinition {
  const BotDefinition({
    required this.botDefinitionId,
    required this.providerId,
    required this.displayName,
    required this.version,
    required this.description,
    required this.botCode,
    required this.supportedRuleSets,
    required this.supportedProtocolVersions,
    required this.visibility,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.strength,
  });

  final String botDefinitionId;
  final String providerId;
  final String displayName;
  final String version;
  final String description;
  final String botCode;
  final String? strength;
  final List<String> supportedRuleSets;
  final List<String> supportedProtocolVersions;
  final BotVisibility visibility;
  final BotDefinitionStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;

  String get fullBotCode => '$providerId-$botCode-$version';

  factory BotDefinition.fromJson(Map<String, dynamic> json) {
    return BotDefinition(
      botDefinitionId: json['bot_definition_id'] as String,
      providerId: json['provider_id'] as String,
      displayName: json['display_name'] as String,
      version: json['version'] as String,
      description: json['description'] as String? ?? '',
      botCode: (json['bot_code'] as String?) ?? '',
      strength: json['strength'] as String? ?? json['difficulty'] as String?,
      supportedRuleSets:
          (json['supported_rule_sets'] as List<dynamic>? ?? const <dynamic>[])
              .map((value) => value.toString())
              .toList(growable: false),
      supportedProtocolVersions:
          (json['supported_protocol_versions'] as List<dynamic>? ??
                  const <dynamic>[])
              .map((value) => value.toString())
              .toList(growable: false),
      visibility: BotVisibility.fromCode(json['visibility'] as String? ?? ''),
      status: BotDefinitionStatus.fromCode(json['status'] as String? ?? ''),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'bot_definition_id': botDefinitionId,
      'provider_id': providerId,
      'display_name': displayName,
      'version': version,
      'description': description,
      'bot_code': botCode,
      if (strength != null) 'strength': strength,
      'supported_rule_sets': supportedRuleSets,
      'supported_protocol_versions': supportedProtocolVersions,
      'visibility': visibility.code,
      'status': status.code,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}

class BotDeployment {
  const BotDeployment({
    required this.deploymentId,
    required this.providerId,
    required this.transportType,
    required this.supportedBotDefinitionIds,
    required this.supportedProtocolVersions,
    required this.maxConcurrentSessions,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.baseUrl,
    this.region,
    this.lastHealthyAt,
    this.lastDeploymentReportedAt,
    this.lastDeploymentGameServerId,
    this.apiKeyHash,
    this.authorizationApiKey,
  });

  final String deploymentId;
  final String providerId;
  final BotTransportType transportType;
  final Uri? baseUrl;
  final List<String> supportedBotDefinitionIds;
  final List<String> supportedProtocolVersions;
  final int maxConcurrentSessions;
  final String? region;
  final BotDeploymentStatus status;
  final DateTime? lastHealthyAt;
  final DateTime? lastDeploymentReportedAt;
  final String? lastDeploymentGameServerId;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// SHA-256 hash of the API key. Only stored server-side; never exposed
  /// to clients via [toJson].
  final String? apiKeyHash;

  /// Optional API key used by the game server when calling an HTTP bot
  /// deployment. This is sensitive and is only serialized for internal
  /// runtime provisioning when explicitly requested.
  final String? authorizationApiKey;

  factory BotDeployment.fromJson(Map<String, dynamic> json) {
    final baseUrl = (json['base_url'] as String?)?.trim();
    return BotDeployment(
      deploymentId: json['deployment_id'] as String,
      providerId: json['provider_id'] as String,
      transportType: BotTransportType.fromCode(
        json['transport_type'] as String? ?? '',
      ),
      baseUrl: baseUrl == null || baseUrl.isEmpty ? null : Uri.parse(baseUrl),
      supportedBotDefinitionIds:
          (json['supported_bot_definition_ids'] as List<dynamic>? ??
                  const <dynamic>[])
              .map((value) => value.toString())
              .toList(growable: false),
      supportedProtocolVersions:
          (json['supported_protocol_versions'] as List<dynamic>? ??
                  const <dynamic>[])
              .map((value) => value.toString())
              .toList(growable: false),
      maxConcurrentSessions: json['max_concurrent_sessions'] as int? ?? 1,
      region: json['region'] as String?,
      status: BotDeploymentStatus.fromCode(json['status'] as String? ?? ''),
      lastHealthyAt: json['last_healthy_at'] == null
          ? null
          : DateTime.parse(json['last_healthy_at'] as String),
      lastDeploymentReportedAt: json['last_deployment_reported_at'] == null
          ? null
          : DateTime.parse(json['last_deployment_reported_at'] as String),
      lastDeploymentGameServerId:
          json['last_deployment_game_server_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      authorizationApiKey: json['authorization_api_key'] as String? ??
          json['api_key'] as String?,
    );
  }

  Map<String, dynamic> toJson({bool includeSensitive = false}) {
    return {
      'deployment_id': deploymentId,
      'provider_id': providerId,
      'transport_type': transportType.code,
      'base_url': baseUrl?.toString(),
      'supported_bot_definition_ids': supportedBotDefinitionIds,
      'supported_protocol_versions': supportedProtocolVersions,
      'max_concurrent_sessions': maxConcurrentSessions,
      'region': region,
      'status': status.code,
      'last_healthy_at': lastHealthyAt?.toIso8601String(),
      'last_deployment_reported_at':
          lastDeploymentReportedAt?.toIso8601String(),
      'last_deployment_game_server_id': lastDeploymentGameServerId,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      if (includeSensitive && authorizationApiKey != null)
        'authorization_api_key': authorizationApiKey,
    };
  }
}

class BotSession {
  const BotSession({
    required this.sessionId,
    required this.botDefinitionId,
    required this.deploymentId,
    required this.gameId,
    required this.playerId,
    required this.seat,
    required this.ruleSet,
    required this.protocolVersion,
    required this.status,
    required this.createdAt,
    this.providerSessionId,
    this.endedAt,
  });

  final String sessionId;
  final String botDefinitionId;
  final String deploymentId;
  final String gameId;
  final String playerId;
  final int seat;
  final String ruleSet;
  final String protocolVersion;
  final String? providerSessionId;
  final BotSessionStatus status;
  final DateTime createdAt;
  final DateTime? endedAt;

  factory BotSession.fromJson(Map<String, dynamic> json) {
    return BotSession(
      sessionId: json['session_id'] as String,
      botDefinitionId: json['bot_definition_id'] as String,
      deploymentId: json['deployment_id'] as String,
      gameId: json['game_id'] as String,
      playerId: json['player_id'] as String,
      seat: json['seat'] as int,
      ruleSet: json['rule_set'] as String,
      protocolVersion: json['protocol_version'] as String,
      providerSessionId: json['provider_session_id'] as String?,
      status: BotSessionStatus.fromCode(json['status'] as String? ?? ''),
      createdAt: DateTime.parse(json['created_at'] as String),
      endedAt: json['ended_at'] == null
          ? null
          : DateTime.parse(json['ended_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'session_id': sessionId,
      'bot_definition_id': botDefinitionId,
      'deployment_id': deploymentId,
      'game_id': gameId,
      'player_id': playerId,
      'seat': seat,
      'rule_set': ruleSet,
      'protocol_version': protocolVersion,
      'provider_session_id': providerSessionId,
      'status': status.code,
      'created_at': createdAt.toIso8601String(),
      'ended_at': endedAt?.toIso8601String(),
    };
  }
}

sealed class BotSeatAssignment {
  const BotSeatAssignment({required this.seat, required this.playerId});

  final int seat;
  final String playerId;

  factory BotSeatAssignment.fromJson(Map<String, dynamic> json) {
    if (json.containsKey('deployment')) {
      return DeployedBotSeatAssignment.fromJson(json);
    }
    return BuiltInBotSeatAssignment.fromJson(json);
  }

  Map<String, dynamic> toJson({bool includeSensitive = false});
}

class DeployedBotSeatAssignment extends BotSeatAssignment {
  const DeployedBotSeatAssignment({
    required super.seat,
    required super.playerId,
    required this.botDefinitionId,
    required this.deployment,
    this.protocolVersion = 'guandan-bot-v1',
    this.botCode = 'WebSocketBot',
  });

  final String botDefinitionId;
  final BotDeployment deployment;
  final String protocolVersion;
  final String botCode;

  factory DeployedBotSeatAssignment.fromJson(Map<String, dynamic> json) {
    return DeployedBotSeatAssignment(
      seat: json['seat'] as int,
      playerId: json['player_id'] as String,
      botDefinitionId: json['bot_definition_id'] as String,
      deployment: BotDeployment.fromJson(
        Map<String, dynamic>.from(json['deployment'] as Map),
      ),
      protocolVersion: json['protocol_version'] as String? ?? 'guandan-bot-v1',
      botCode: json['bot_model'] as String? ?? 'WebSocketBot',
    );
  }

  @override
  Map<String, dynamic> toJson({bool includeSensitive = false}) {
    return {
      'seat': seat,
      'player_id': playerId,
      'bot_definition_id': botDefinitionId,
      'deployment': deployment.toJson(includeSensitive: includeSensitive),
      'protocol_version': protocolVersion,
      'bot_model': botCode,
    };
  }
}

class BuiltInBotSeatAssignment extends BotSeatAssignment {
  const BuiltInBotSeatAssignment({
    required super.seat,
    required super.playerId,
    required this.botCode,
  });

  final String botCode;

  factory BuiltInBotSeatAssignment.fromJson(Map<String, dynamic> json) {
    return BuiltInBotSeatAssignment(
      seat: json['seat'] as int,
      playerId: json['player_id'] as String,
      botCode: (json['bot_code'] as String?) ?? '',
    );
  }

  @override
  Map<String, dynamic> toJson({bool includeSensitive = false}) {
    return {
      'seat': seat,
      'player_id': playerId,
      'bot_code': botCode,
    };
  }
}

class RegisterBotProviderRequest {
  const RegisterBotProviderRequest({
    required this.displayName,
    required this.contactEmail,
  });

  final String displayName;
  final String contactEmail;

  factory RegisterBotProviderRequest.fromJson(Map<String, dynamic> json) {
    return RegisterBotProviderRequest(
      displayName: (json['display_name'] as String? ?? '').trim(),
      contactEmail: (json['contact_email'] as String? ?? '').trim(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'display_name': displayName,
      'contact_email': contactEmail,
    };
  }
}

class CreateBotDefinitionRequest {
  const CreateBotDefinitionRequest({
    required this.providerId,
    required this.displayName,
    required this.version,
    required this.description,
    required this.botCode,
    required this.supportedRuleSets,
    required this.supportedProtocolVersions,
    this.strength,
    this.visibility = BotVisibility.private,
  });

  final String providerId;
  final String displayName;
  final String version;
  final String description;
  final String botCode;
  final String? strength;
  final List<String> supportedRuleSets;
  final List<String> supportedProtocolVersions;
  final BotVisibility visibility;

  factory CreateBotDefinitionRequest.fromJson(Map<String, dynamic> json) {
    return CreateBotDefinitionRequest(
      providerId: (json['provider_id'] as String? ?? '').trim(),
      displayName: (json['display_name'] as String? ?? '').trim(),
      version: (json['version'] as String? ?? '').trim(),
      description: (json['description'] as String? ?? '').trim(),
      botCode: (json['bot_code'] as String?)?.trim() ?? '',
      strength: (json['strength'] as String?)?.trim() ??
          (json['difficulty'] as String?)?.trim(),
      supportedRuleSets:
          (json['supported_rule_sets'] as List<dynamic>? ?? const <dynamic>[])
              .map((value) => value.toString().trim())
              .where((value) => value.isNotEmpty)
              .toList(growable: false),
      supportedProtocolVersions:
          (json['supported_protocol_versions'] as List<dynamic>? ??
                  const <dynamic>[])
              .map((value) => value.toString().trim())
              .where((value) => value.isNotEmpty)
              .toList(growable: false),
      visibility: BotVisibility.fromCode(json['visibility'] as String? ?? ''),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'provider_id': providerId,
      'display_name': displayName,
      'version': version,
      'description': description,
      'bot_code': botCode,
      if (strength != null) 'strength': strength,
      'supported_rule_sets': supportedRuleSets,
      'supported_protocol_versions': supportedProtocolVersions,
      'visibility': visibility.code,
    };
  }
}

class RegisterBotDeploymentRequest {
  const RegisterBotDeploymentRequest({
    required this.providerId,
    required this.transportType,
    required this.supportedBotDefinitionIds,
    required this.supportedProtocolVersions,
    required this.maxConcurrentSessions,
    this.baseUrl,
    this.region,
    this.authorizationApiKey,
  });

  final String providerId;
  final BotTransportType transportType;
  final Uri? baseUrl;
  final List<String> supportedBotDefinitionIds;
  final List<String> supportedProtocolVersions;
  final int maxConcurrentSessions;
  final String? region;

  /// Deprecated for HTTP deployments. The platform issues the invocation token
  /// and returns it as [BotRegistrationResponse.botInvocationToken].
  final String? authorizationApiKey;

  factory RegisterBotDeploymentRequest.fromJson(Map<String, dynamic> json) {
    final baseUrl = (json['base_url'] as String?)?.trim();
    return RegisterBotDeploymentRequest(
      providerId: (json['provider_id'] as String? ?? '').trim(),
      transportType: BotTransportType.fromCode(
        json['transport_type'] as String? ?? '',
      ),
      baseUrl: baseUrl == null || baseUrl.isEmpty ? null : Uri.parse(baseUrl),
      supportedBotDefinitionIds:
          (json['supported_bot_definition_ids'] as List<dynamic>? ??
                  const <dynamic>[])
              .map((value) => value.toString().trim())
              .where((value) => value.isNotEmpty)
              .toList(growable: false),
      supportedProtocolVersions:
          (json['supported_protocol_versions'] as List<dynamic>? ??
                  const <dynamic>[])
              .map((value) => value.toString().trim())
              .where((value) => value.isNotEmpty)
              .toList(growable: false),
      maxConcurrentSessions: json['max_concurrent_sessions'] as int? ?? 1,
      region: (json['region'] as String?)?.trim(),
      authorizationApiKey: (json['authorization_api_key'] as String?)?.trim() ??
          (json['api_key'] as String?)?.trim(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'provider_id': providerId,
      'transport_type': transportType.code,
      'base_url': baseUrl?.toString(),
      'supported_bot_definition_ids': supportedBotDefinitionIds,
      'supported_protocol_versions': supportedProtocolVersions,
      'max_concurrent_sessions': maxConcurrentSessions,
      'region': region,
      if (authorizationApiKey != null && authorizationApiKey!.isNotEmpty)
        'api_key': authorizationApiKey,
    };
  }
}

class BotRegistrationResponse {
  const BotRegistrationResponse({
    this.provider,
    this.definition,
    this.deployment,
    this.apiKey,
    this.deploymentManagementKey,
    this.botInvocationToken,
  });

  final BotProvider? provider;
  final BotDefinition? definition;
  final BotDeployment? deployment;

  /// Deprecated alias for [deploymentManagementKey].
  final String? apiKey;

  /// Plaintext deployment management key. Only returned once on deployment
  /// creation. The server stores only the hash.
  final String? deploymentManagementKey;

  /// Plaintext token that runtime game servers use to authenticate calls to an
  /// HTTP bot deployment. Only returned once on deployment creation and only
  /// serialized internally after that.
  final String? botInvocationToken;

  factory BotRegistrationResponse.fromJson(Map<String, dynamic> json) {
    return BotRegistrationResponse(
      provider: json['provider'] == null
          ? null
          : BotProvider.fromJson(
              Map<String, dynamic>.from(json['provider'] as Map),
            ),
      definition: json['definition'] == null
          ? null
          : BotDefinition.fromJson(
              Map<String, dynamic>.from(json['definition'] as Map),
            ),
      deployment: json['deployment'] == null
          ? null
          : BotDeployment.fromJson(
              Map<String, dynamic>.from(json['deployment'] as Map),
            ),
      apiKey: json['api_key'] as String?,
      deploymentManagementKey: json['deployment_management_key'] as String? ??
          json['api_key'] as String?,
      botInvocationToken: json['bot_invocation_token'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (provider != null) 'provider': provider!.toJson(),
      if (definition != null) 'definition': definition!.toJson(),
      if (deployment != null) 'deployment': deployment!.toJson(),
      if ((deploymentManagementKey ?? apiKey) != null) ...{
        'deployment_management_key': deploymentManagementKey ?? apiKey,
        'api_key': deploymentManagementKey ?? apiKey,
      },
      if (botInvocationToken != null)
        'bot_invocation_token': botInvocationToken,
    };
  }
}

class VerifyBotDeploymentRequest {
  const VerifyBotDeploymentRequest({
    required this.baseUrl,
  });

  final Uri baseUrl;

  factory VerifyBotDeploymentRequest.fromJson(Map<String, dynamic> json) {
    final baseUrl = (json['base_url'] as String? ?? '').trim();
    return VerifyBotDeploymentRequest(baseUrl: Uri.parse(baseUrl));
  }

  Map<String, dynamic> toJson() {
    return {'base_url': baseUrl.toString()};
  }
}

class BotDiscoveryResponse {
  const BotDiscoveryResponse({
    required this.providers,
    required this.definitions,
    required this.deployments,
  });

  final List<BotProvider> providers;
  final List<BotDefinition> definitions;
  final List<BotDeployment> deployments;

  factory BotDiscoveryResponse.fromJson(Map<String, dynamic> json) {
    return BotDiscoveryResponse(
      providers: (json['providers'] as List<dynamic>? ?? const <dynamic>[])
          .map((value) =>
              BotProvider.fromJson(Map<String, dynamic>.from(value as Map)))
          .toList(growable: false),
      definitions: (json['definitions'] as List<dynamic>? ?? const <dynamic>[])
          .map((value) =>
              BotDefinition.fromJson(Map<String, dynamic>.from(value as Map)))
          .toList(growable: false),
      deployments: (json['deployments'] as List<dynamic>? ?? const <dynamic>[])
          .map((value) =>
              BotDeployment.fromJson(Map<String, dynamic>.from(value as Map)))
          .toList(growable: false),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'providers': providers
          .map((provider) => provider.toJson())
          .toList(growable: false),
      'definitions': definitions
          .map((definition) => definition.toJson())
          .toList(growable: false),
      'deployments': deployments
          .map((deployment) => deployment.toJson())
          .toList(growable: false),
    };
  }
}

/// Event type for bot deployment lifecycle reports from game servers.
enum BotDeploymentEventType {
  connected('connected'),
  disconnected('disconnected');

  const BotDeploymentEventType(this.code);

  final String code;

  static BotDeploymentEventType fromCode(String code) {
    return BotDeploymentEventType.values.firstWhere(
      (type) => type.code == code,
      orElse: () => BotDeploymentEventType.connected,
    );
  }
}

/// Report sent from a game server to the lobby when a bot deployment
/// connects to or disconnects from the bot gateway pool.
class BotDeploymentEventReport {
  const BotDeploymentEventReport({
    required this.gameServerId,
    required this.deploymentId,
    required this.eventType,
    required this.occurredAt,
  });

  final String gameServerId;
  final String deploymentId;
  final BotDeploymentEventType eventType;
  final DateTime occurredAt;

  factory BotDeploymentEventReport.fromJson(Map<String, dynamic> json) {
    return BotDeploymentEventReport(
      gameServerId: json['game_server_id'] as String,
      deploymentId: json['deployment_id'] as String,
      eventType: BotDeploymentEventType.fromCode(
        json['event_type'] as String? ?? '',
      ),
      occurredAt: DateTime.parse(json['occurred_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'game_server_id': gameServerId,
      'deployment_id': deploymentId,
      'event_type': eventType.code,
      'occurred_at': occurredAt.toIso8601String(),
    };
  }
}

/// Health status of a deployed bot as reported by a game server.
class BotDeploymentHealthResponse {
  const BotDeploymentHealthResponse({
    required this.deploymentId,
    required this.connected,
    this.gameServerId,
    required this.checkedAt,
    this.error,
  });

  final String deploymentId;
  final bool connected;
  final String? gameServerId;
  final DateTime checkedAt;
  final String? error;

  factory BotDeploymentHealthResponse.fromJson(Map<String, dynamic> json) {
    return BotDeploymentHealthResponse(
      deploymentId: json['deployment_id'] as String,
      connected: json['connected'] as bool? ?? false,
      gameServerId: json['game_server_id'] as String?,
      checkedAt: DateTime.parse(json['checked_at'] as String),
      error: json['error'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'deployment_id': deploymentId,
      'connected': connected,
      'game_server_id': gameServerId,
      'checked_at': checkedAt.toIso8601String(),
      if (error != null) 'error': error,
    };
  }
}
