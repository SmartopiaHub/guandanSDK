/// Typed bot parameters: the parameter list declared by a bot definition.
///
/// Only three parameter types are supported: integer, boolean, and string.
/// The definition schema is exposed to the UI, so developers/admins can set
/// values; the effective values are passed to the game server when the bot is
/// realized and to deployed bots via `SessionStartMessage.params`.
library;

/// The supported bot parameter types.
enum BotParameterType {
  integer('integer'),
  boolean('boolean'),
  string('string');

  const BotParameterType(this.code);

  /// Wire code: `'integer' | 'boolean' | 'string'`.
  final String code;

  static BotParameterType fromCode(String code) {
    return BotParameterType.values.firstWhere(
      (type) => type.code == code,
      // Unknown types degrade to string (no constraint machinery applies),
      // mirroring the lenient fromCode pattern of the registry enums.
      orElse: () => BotParameterType.string,
    );
  }
}

/// One declared parameter of a bot definition.
///
/// Integer parameters may declare [min]/[max] bounds (inclusive); string
/// parameters may declare a non-empty [choices] enumeration (e.g.
/// `['max', 'median', 'low']`). Boolean parameters take no constraints.
/// The [defaultValue] (when present) must itself satisfy the constraints:
/// an `int` for [BotParameterType.integer], a `bool` for
/// [BotParameterType.boolean], or a `String` for [BotParameterType.string].
class BotParameterDefinition {
  const BotParameterDefinition({
    required this.name,
    required this.type,
    this.defaultValue,
    this.min,
    this.max,
    this.choices,
    this.description,
  });

  /// The parameter name; must be unique within a definition's list.
  final String name;

  final BotParameterType type;

  /// The default value (null = no default). Must satisfy the constraints.
  final Object? defaultValue;

  /// Integer-only inclusive lower bound.
  final int? min;

  /// Integer-only inclusive upper bound.
  final int? max;

  /// String-only enumeration of acceptable values (non-empty).
  final List<String>? choices;

  /// Optional human-readable description shown in the UI.
  final String? description;

  factory BotParameterDefinition.fromJson(Map<String, dynamic> json) {
    return BotParameterDefinition(
      name: (json['name'] as String? ?? '').trim(),
      type: BotParameterType.fromCode(json['type'] as String? ?? ''),
      defaultValue: json['default'],
      min: (json['min'] as num?)?.toInt(),
      max: (json['max'] as num?)?.toInt(),
      choices: json['choices'] == null
          ? null
          : (json['choices'] as List<dynamic>)
              .map((value) => value.toString())
              .toList(growable: false),
      description: json['description'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'type': type.code,
      if (defaultValue != null) 'default': defaultValue,
      if (min != null) 'min': min,
      if (max != null) 'max': max,
      if (choices != null) 'choices': choices,
      if (description != null && description!.isNotEmpty)
        'description': description,
    };
  }
}
