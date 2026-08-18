/// The catalog of platform built-in bots: their codes, display names, and
/// typed parameter schemas.
///
/// Shared by the Flutter app (bot selection UI), the lobby server (seat
/// validation + defaults), and the game server (realization). Keeping the
/// schemas here ensures the three consumers agree on the same parameter list.
library;

import 'contracts/bot_parameter_contract.dart';

/// One built-in bot: code, display name, and declared parameter schema.
class BuiltInBotSpec {
  const BuiltInBotSpec({
    required this.botCode,
    required this.displayName,
    this.parameters = const <BotParameterDefinition>[],
  });

  /// The bot code used in seat assignments, e.g. `tactician`.
  final String botCode;

  /// The display name shown in the client UI.
  final String displayName;

  /// The typed parameters the bot accepts (empty for bots without knobs).
  final List<BotParameterDefinition> parameters;
}

/// The platform's built-in bots with their parameter schemas.
const builtInBotCatalog = <BuiltInBotSpec>[
  BuiltInBotSpec(
    botCode: 'basicBot',
    displayName: 'Basic Bot',
  ),
  BuiltInBotSpec(
    botCode: 'strongBot',
    displayName: 'Strong Bot',
  ),
  BuiltInBotSpec(
    botCode: 'tactician',
    displayName: 'Tactician Bot',
    parameters: [
      BotParameterDefinition(
        name: 'strength',
        type: BotParameterType.integer,
        defaultValue: 50,
        min: 0,
        description:
            'Maximum rule strength; rules with a higher strength are ignored '
            '(default 50).',
      ),
    ],
  ),
];

/// Looks up a built-in spec by code (case-insensitive); null when the code
/// is not a known built-in.
BuiltInBotSpec? builtInBotSpecForCode(String botCode) {
  final normalized = botCode.toLowerCase();
  for (final spec in builtInBotCatalog) {
    if (spec.botCode.toLowerCase() == normalized) return spec;
  }
  return null;
}
