

/// Configuration for per-action time limits during a game.
///
/// Each limit is specified in seconds. A `null` value means no limit for that
/// action. The [extraTime] constant (60 s) is granted once per player per game
/// when [GameRoomConfig.allowExtraTime] is enabled. [delegatedActionDelay]
/// (default 4 s) is the delay before an automatically delegated bot begins its
/// action. After that delay, the bot receives the normal room action budget.
class TimingConfig {
  final int? _playTimeLimit;
  final int? _tributeTimeLimit;
  final int? _returnTimeLimit;
  final int? _sortTimeLimit;
  final int? _delegatedActionDelay;

  /// Extra time granted once per player per game (60 seconds).
  static const Duration extraTime = Duration(seconds: 60);

  /// Total time limit for the opening phase (until every player has played their
  /// first hand), in seconds.
  final int? _openingTimeLimit;

  /// Maximum time allowed per play turn, or `null` if unlimited.
  Duration? get playTimeLimit => _playTimeLimit == null ? null : Duration(seconds: _playTimeLimit);
  /// Maximum time allowed to pay tribute, or `null` if unlimited.
  Duration? get tributeTimeLimit => _tributeTimeLimit == null ? null : Duration(seconds: _tributeTimeLimit);
  /// Maximum time allowed to return a tribute card, or `null` if unlimited.
  Duration? get returnTimeLimit => _returnTimeLimit == null ? null : Duration(seconds: _returnTimeLimit);
  /// Maximum time allowed to sort cards at round start, or `null` if unlimited.
  Duration? get sortTimeLimit => _sortTimeLimit == null ? null : Duration(seconds: _sortTimeLimit);
  /// Maximum time for the opening phase, or `null` if unlimited.
  Duration? get openingTimeLimit => _openingTimeLimit == null ? null : Duration(seconds: _openingTimeLimit);
  /// Delay before an automatically delegated bot acts, or `null` to use the
  /// default (4 s).
  Duration? get delegatedActionDelay => _delegatedActionDelay == null ? null : Duration(seconds: _delegatedActionDelay);

  /// Whether any time limit is configured.
  bool get isTimed => _playTimeLimit != null || tributeTimeLimit != null || returnTimeLimit != null || sortTimeLimit != null || _openingTimeLimit != null;

  /// Creates a [TimingConfig] with optional limits in seconds.
  /// [delegatedActionDelay] defaults to 4 seconds.
  TimingConfig({int? playTimeLimit, int? tributeTimeLimit, int? returnTimeLimit, int? sortTimeLimit, int? openingTimeLimit, int? delegatedActionDelay}):
    _playTimeLimit = playTimeLimit,
    _tributeTimeLimit = tributeTimeLimit,
    _returnTimeLimit = returnTimeLimit,
    _sortTimeLimit = sortTimeLimit,
    _delegatedActionDelay = delegatedActionDelay ?? 4,
    _openingTimeLimit = openingTimeLimit;

  /// Deserializes a [TimingConfig] from a JSON map.
  TimingConfig.fromJson(Map<String, dynamic> json)
      : _playTimeLimit = json['play_time_limit'] as int?,
        _tributeTimeLimit = json['tribute_time_limit'] as int?,
        _returnTimeLimit = json['return_time_limit'] as int?,
        _sortTimeLimit = json['sort_time_limit'] as int?,
        _delegatedActionDelay = json['delegated_action_delay'] as int? ?? 4,
        _openingTimeLimit = json['opening_time_limit'] as int?;

  /// Creates a copy with the given fields replaced.
  TimingConfig copyWith({
    int? playTimeLimit,
    int? tributeTimeLimit,
    int? returnTimeLimit,
    int? sortTimeLimit,
    int? openingTimeLimit,
    int? delegatedActionDelay,
  }) {
    return TimingConfig(
      playTimeLimit: playTimeLimit ?? _playTimeLimit,
      tributeTimeLimit: tributeTimeLimit ?? _tributeTimeLimit,
      returnTimeLimit: returnTimeLimit ?? _returnTimeLimit,
      sortTimeLimit: sortTimeLimit ?? _sortTimeLimit,
      openingTimeLimit: openingTimeLimit ?? _openingTimeLimit,
      delegatedActionDelay: delegatedActionDelay ?? _delegatedActionDelay,
    );
  }

  /// Serializes the timing config to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'play_time_limit': _playTimeLimit,
      'tribute_time_limit': _tributeTimeLimit,
      'return_time_limit': _returnTimeLimit,
      'sort_time_limit': _sortTimeLimit,
      'opening_time_limit': _openingTimeLimit,
      'delegated_action_delay': _delegatedActionDelay,
    };
  }
}


/// Predefined timing presets for game rooms.
enum PresetTimingMode{
  /// Short action limits (30 s play, 60 s tribute, 90 s return, 120 s opening).
  fastPaced,
  /// Generous limits (99 s for all timed actions).
  relaxed,
  /// No time limits at all.
  noLimit,
}

/// Creates a [TimingConfig] from a [PresetTimingMode].
TimingConfig createPresetTimingConfig(PresetTimingMode timingMode){
    switch(timingMode){
      case PresetTimingMode.noLimit:
        return TimingConfig();
      case PresetTimingMode.fastPaced:
        return TimingConfig(playTimeLimit: 30, tributeTimeLimit: 60, returnTimeLimit: 90, openingTimeLimit: 120);
      case PresetTimingMode.relaxed:
        return TimingConfig(playTimeLimit: 99, tributeTimeLimit: 99, returnTimeLimit: 99);
    }
  }

/// Immutable configuration for a game room that governs gameplay rules.
///
/// Includes player count, tribute/ace-passing settings, timing, and
/// privacy/social flags for bot nicknames and player-leave broadcasts.
class GameRoomConfig{

  /// Maximum number of players allowed in the room. Currently must be 4.
  final int requiredPlayers;

  /// Whether the tribute (进贡) stage is enabled after each round.
  bool tributeEnabled;

  /// When tribute is disabled, whether play starts from the banker.
  /// When `false` (and [tributeEnabled] is `false`), a random player starts.
  bool bankerFirstWhenNoTribute;

  /// Room tier level, used for matchmaking or filtering.
  int roomTier;

  /// Whether the Ace-passing (过尖) feature is enabled.
  bool acePassingEnabled;

  /// Optional room password for private rooms.
  String? password;

  /// When `false`, human-like random nicknames are used for bots.
  /// When `true` (default), bot-specific nicknames are used.
  bool useBotNicknames;

  /// When `false`, bot model metadata is hidden from client join messages
  /// (for privacy in social/friend rooms). When `true` (default), exposed.
  bool exposeBotCode;

  /// When `true`, broadcast optional social leave notifications.
  /// In-game replacement messages are always broadcast because clients need
  /// them to replace the leaving player's seat/avatar with the delegate bot.
  bool broadcastPlayerLeave;

  /// The delay for bot actions to simulate human behavior, in milliseconds.
  /// 0 means use the server default. Set to a positive value (e.g. 1000 for
  /// 1 second) to override.
  int botDelay;

  /// Whether the room has any time limits configured.
  bool get isTimed => timingConfig.isTimed;

  /// Whether extra time (60 s once per player) is allowed.
  final bool allowExtraTime;

  static final TimingConfig _defaultTimingConfig = createPresetTimingConfig(PresetTimingMode.relaxed);

  TimingConfig get timingConfig => _timingConfig ?? _defaultTimingConfig;
  set timingConfig(TimingConfig? timingConfig){
    _timingConfig = timingConfig;
  }

  /// Extra time granted once per player (e.g., 60 s), or `null` if not allowed.
  Duration? get extraTime => allowExtraTime ? TimingConfig.extraTime : null;

  

  Duration? get playTimeLimit => timingConfig.playTimeLimit;
  Duration? get tributeTimeLimit => timingConfig.tributeTimeLimit;
  Duration? get returnTimeLimit => timingConfig.returnTimeLimit;
  Duration? get sortTimeLimit => timingConfig.sortTimeLimit;
  Duration? get openingTimeLimit => timingConfig.openingTimeLimit;
  /// Delay before an automatically delegated bot begins its action.
  Duration? get delegatedActionDelay => timingConfig.delegatedActionDelay;

  TimingConfig? _timingConfig;

  /// Creates a game room configuration with the specified parameters.
  /// [requiredPlayers] is the maximum number of players allowed in the room. Currently, it must be 4.
  /// [acePassingEnabled] indicates whether 过尖 feature is enabled.
  /// [timingConfig] allows for custom timing configurations, overriding the default based on [timingMode].
  /// [roomTier] specifies the room level, defaulting to 0 if not provided.
  GameRoomConfig({required this.requiredPlayers, this.acePassingEnabled=true, this.roomTier=0,
    this.tributeEnabled=true, this.bankerFirstWhenNoTribute=true, this.allowExtraTime=true,
     this.password, TimingConfig? timingConfig,
     this.useBotNicknames = true, this.exposeBotCode = true, this.broadcastPlayerLeave = false,
     this.botDelay = 0}):
    _timingConfig = timingConfig;


  factory GameRoomConfig.fourPlayers()  {
    return GameRoomConfig(requiredPlayers: 4);
  }

  GameRoomConfig.fromJson(Map<String, dynamic> json)
      : requiredPlayers = json['required_players'] as int,
        roomTier = json['room_tier'] as int? ?? 0,
        acePassingEnabled = json['ace_plus_enabled'] as bool? ?? true,
        tributeEnabled = json['tribute_enabled'] as bool? ?? true,
        allowExtraTime = json['allow_extra_time'] as bool? ?? true,
        bankerFirstWhenNoTribute = json['banker_first_when_no_tribute'] as bool? ?? true,
        password = json['password'] as String?,
        useBotNicknames = json['use_bot_nicknames'] as bool? ?? true,
        exposeBotCode = json['expose_bot_code'] as bool? ?? true,
        broadcastPlayerLeave = json['broadcast_player_leave'] as bool? ?? false,
        botDelay = json['bot_delay'] as int? ?? 0;


  /// Creates a copy with the given fields replaced.
  GameRoomConfig copyWith({
    int? requiredPlayers,
    bool? tributeEnabled,
    bool? bankerFirstWhenNoTribute,
    int? roomTier,
    bool? acePassingEnabled,
    String? password,
    bool? allowExtraTime,
    TimingConfig? timingConfig,
    bool? useBotNicknames,
    bool? exposeBotCode,
    bool? broadcastPlayerLeave,
    int? botDelay,
  }) {
    return GameRoomConfig(
      requiredPlayers: requiredPlayers ?? this.requiredPlayers,
      tributeEnabled: tributeEnabled ?? this.tributeEnabled,
      bankerFirstWhenNoTribute: bankerFirstWhenNoTribute ?? this.bankerFirstWhenNoTribute,
      roomTier: roomTier ?? this.roomTier,
      acePassingEnabled: acePassingEnabled ?? this.acePassingEnabled,
      password: password ?? this.password,
      allowExtraTime: allowExtraTime ?? this.allowExtraTime,
      timingConfig: timingConfig ?? _timingConfig,
      useBotNicknames: useBotNicknames ?? this.useBotNicknames,
      exposeBotCode: exposeBotCode ?? this.exposeBotCode,
      broadcastPlayerLeave: broadcastPlayerLeave ?? this.broadcastPlayerLeave,
      botDelay: botDelay ?? this.botDelay,
    );
  }

  /// Serializes the room config to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'required_players': requiredPlayers,
      'room_tier': roomTier,
      'ace_plus_enabled': acePassingEnabled,
      'password': password,
      'allow_extra_time': allowExtraTime,
      'tribute_enabled': tributeEnabled,
      'banker_first_when_no_tribute': bankerFirstWhenNoTribute,
      'use_bot_nicknames': useBotNicknames,
      'expose_bot_code': exposeBotCode,
      'broadcast_player_leave': broadcastPlayerLeave,
      'bot_delay': botDelay,
    };
  }
}

/// Metadata about a game room, persisted alongside the room.
///
/// Contains the room's identity (ID, creator, owner, creation time) and its
/// [GameRoomConfig]. The [password] getter is a convenience for the config's
/// password field.
class RoomMetadata {
  /// The room's unique identifier.
  final String roomId;
  /// The player ID of the room creator.
  final String creatorId;
  /// When the room was created.
  final DateTime creationTime;
  /// The current room owner's player ID. May differ from [creatorId] if
  /// ownership was transferred.
  String? ownerId;
  /// The room's gameplay configuration.
  late final GameRoomConfig config;

  /// Shortcut for the room password from the config, or `null` if none is set.
  String? get password => config.password;

  /// Creates room metadata. If no [config] is given, defaults to a 4-player room.
  RoomMetadata(this.roomId, this.creatorId, this.creationTime, this.ownerId,
    {GameRoomConfig? config}): config = config ?? GameRoomConfig.fourPlayers();

  /// Deserializes [RoomMetadata] from a JSON map.
  RoomMetadata.fromJson(Map<String, dynamic> json)
      : roomId = json['room_id'] as String,
        creatorId = json['creator_id'] as String,
        creationTime = DateTime.parse(json['creation_time'] as String),
        ownerId = json['room_owner_id'] as String?,
        config = GameRoomConfig.fromJson(json['config'] as Map<String, dynamic>);

  /// Creates a copy with the given fields replaced.
  RoomMetadata copyWith({
    String? roomId,
    String? creatorId,
    DateTime? creationTime,
    String? ownerId,
    GameRoomConfig? config,
  }) {
    return RoomMetadata(
      roomId ?? this.roomId,
      creatorId ?? this.creatorId,
      creationTime ?? this.creationTime,
      ownerId ?? this.ownerId,
      config: config ?? this.config,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'room_id': roomId,
      'creator_id': creatorId,
      'creation_time': creationTime.toIso8601String(),
      'room_owner_id': ownerId,
      'config': config.toJson(),
    };
  }
}
