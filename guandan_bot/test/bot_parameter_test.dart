import 'package:guandan_bot/guandan_bot.dart';
import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

void main() {
  group('BotParameterDefinition JSON', () {
    test('round-trips all fields', () {
      const definition = BotParameterDefinition(
        name: 'strength',
        type: BotParameterType.integer,
        defaultValue: 50,
        min: 0,
        max: 100,
        description: 'Maximum rule strength.',
      );
      final decoded =
          BotParameterDefinition.fromJson(definition.toJson());
      expect(decoded.name, 'strength');
      expect(decoded.type, BotParameterType.integer);
      expect(decoded.defaultValue, 50);
      expect(decoded.min, 0);
      expect(decoded.max, 100);
      expect(decoded.description, 'Maximum rule strength.');
      expect(decoded.choices, isNull);
    });

    test('round-trips choices for string parameters', () {
      const definition = BotParameterDefinition(
        name: 'mode',
        type: BotParameterType.string,
        defaultValue: 'median',
        choices: ['max', 'median', 'low'],
      );
      final decoded = BotParameterDefinition.fromJson(definition.toJson());
      expect(decoded.type, BotParameterType.string);
      expect(decoded.defaultValue, 'median');
      expect(decoded.choices, ['max', 'median', 'low']);
    });

    test('omits absent optional keys from JSON (legacy byte-compatible)', () {
      const definition = BotParameterDefinition(
        name: 'aggressive',
        type: BotParameterType.boolean,
      );
      final json = definition.toJson();
      expect(json.keys.toSet(), {'name', 'type'});
    });

    test('tolerates missing keys on decode', () {
      final decoded = BotParameterDefinition.fromJson(const {
        'name': 'strength',
      });
      expect(decoded.name, 'strength');
      expect(decoded.type, BotParameterType.string); // lenient fallback
      expect(decoded.defaultValue, isNull);
      expect(decoded.min, isNull);
      expect(decoded.max, isNull);
      expect(decoded.choices, isNull);
    });

    test('unknown type code degrades to string', () {
      final decoded = BotParameterDefinition.fromJson(const {
        'name': 'x',
        'type': 'float',
      });
      expect(decoded.type, BotParameterType.string);
    });
  });

  group('validateParameterDefinition', () {
    test('accepts valid integer, boolean, and string definitions', () {
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'strength',
          type: BotParameterType.integer,
          defaultValue: 50,
          min: 0,
        )),
        isEmpty,
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'aggressive',
          type: BotParameterType.boolean,
          defaultValue: false,
        )),
        isEmpty,
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'mode',
          type: BotParameterType.string,
          defaultValue: 'median',
          choices: ['max', 'median', 'low'],
        )),
        isEmpty,
      );
    });

    test('rejects empty names', () {
      expect(
        validateParameterDefinition(
            const BotParameterDefinition(name: '', type: BotParameterType.integer)),
        isNotEmpty,
      );
    });

    test('rejects min > max', () {
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 's',
          type: BotParameterType.integer,
          min: 10,
          max: 1,
        )),
        contains(contains('min must be <= max')),
      );
    });

    test('rejects constraints on the wrong type', () {
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'b',
          type: BotParameterType.boolean,
          min: 1,
        )),
        contains(contains('not valid for boolean')),
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'i',
          type: BotParameterType.integer,
          choices: ['a'],
        )),
        contains(contains('only valid for string')),
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 's',
          type: BotParameterType.string,
          min: 1,
        )),
        contains(contains('only valid for integer')),
      );
    });

    test('rejects empty choices', () {
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 's',
          type: BotParameterType.string,
          choices: [],
        )),
        contains(contains('choices must not be empty')),
      );
    });

    test('rejects defaults of the wrong type', () {
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'i',
          type: BotParameterType.integer,
          defaultValue: 'fifty',
        )),
        contains(contains('default must be an integer')),
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 'b',
          type: BotParameterType.boolean,
          defaultValue: 1,
        )),
        contains(contains('default must be a boolean')),
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 's',
          type: BotParameterType.string,
          defaultValue: 50,
        )),
        contains(contains('default must be a string')),
      );
    });

    test('rejects defaults outside the constraints', () {
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 's',
          type: BotParameterType.integer,
          defaultValue: 5,
          min: 10,
        )),
        contains(contains('default must be >= 10')),
      );
      expect(
        validateParameterDefinition(const BotParameterDefinition(
          name: 's',
          type: BotParameterType.string,
          defaultValue: 'extreme',
          choices: ['max', 'median', 'low'],
        )),
        contains(contains('must be one of')),
      );
    });
  });

  group('resolveEffectiveParameters', () {
    const schema = [
      BotParameterDefinition(
        name: 'strength',
        type: BotParameterType.integer,
        defaultValue: 50,
        min: 0,
        max: 100,
      ),
      BotParameterDefinition(
        name: 'aggressive',
        type: BotParameterType.boolean,
        defaultValue: false,
      ),
      BotParameterDefinition(
        name: 'mode',
        type: BotParameterType.string,
        defaultValue: 'median',
        choices: ['max', 'median', 'low'],
      ),
    ];

    test('uses definition defaults when no values are set', () {
      final resolution = resolveEffectiveParameters(schema: schema);
      expect(resolution.isValid, isTrue);
      expect(resolution.effective, {
        'strength': 50,
        'aggressive': false,
        'mode': 'median',
      });
    });

    test('deployment values override defaults, seat values override both', () {
      final resolution = resolveEffectiveParameters(
        schema: schema,
        deploymentValues: const {'strength': 30, 'aggressive': true},
        seatValues: const {'strength': 25},
      );
      expect(resolution.isValid, isTrue);
      expect(resolution.effective, {
        'strength': 25,
        'aggressive': true,
        'mode': 'median',
      });
    });

    test('rejects unknown parameter names', () {
      final resolution = resolveEffectiveParameters(
        schema: schema,
        seatValues: const {'bogus': 1},
      );
      expect(resolution.isValid, isFalse);
      expect(resolution.errors, contains(contains('unknown parameter')));
      // Known parameters still resolve.
      expect(resolution.effective['strength'], 50);
    });

    test('rejects wrong-typed values', () {
      final resolution = resolveEffectiveParameters(
        schema: schema,
        seatValues: const {'strength': 'fifty'},
      );
      expect(resolution.isValid, isFalse);
      expect(resolution.errors, contains(contains('must be an integer')));
      // Invalid value is excluded; default remains.
      expect(resolution.effective['strength'], 50);
    });

    test('rejects out-of-range integer values', () {
      final resolution = resolveEffectiveParameters(
        schema: schema,
        seatValues: const {'strength': -5},
      );
      expect(resolution.isValid, isFalse);
      expect(resolution.errors, contains(contains('must be >= 0')));
      expect(resolution.effective['strength'], 50);

      final above = resolveEffectiveParameters(
        schema: schema,
        seatValues: const {'strength': 500},
      );
      expect(above.isValid, isFalse);
      expect(above.errors, contains(contains('must be <= 100')));
    });

    test('rejects values not in the choices enumeration', () {
      final resolution = resolveEffectiveParameters(
        schema: schema,
        seatValues: const {'mode': 'extreme'},
      );
      expect(resolution.isValid, isFalse);
      expect(resolution.errors, contains(contains('must be one of')));
      expect(resolution.effective['mode'], 'median');
    });

    test('accepts values within constraints', () {
      final resolution = resolveEffectiveParameters(
        schema: schema,
        deploymentValues: const {'strength': 0, 'mode': 'max'},
        seatValues: const {'strength': 100},
      );
      expect(resolution.isValid, isTrue);
      expect(resolution.effective['strength'], 100);
      expect(resolution.effective['mode'], 'max');
    });
  });

  group('builtInBotCatalog', () {
    test('looks up specs case-insensitively', () {
      expect(builtInBotSpecForCode('tactician')?.botCode, 'tactician');
      expect(builtInBotSpecForCode('TACTICIAN')?.botCode, 'tactician');
      expect(builtInBotSpecForCode('strongBot')?.displayName, 'Strong Bot');
      expect(builtInBotSpecForCode('basicBot')?.displayName, 'Basic Bot');
      expect(builtInBotSpecForCode('unknown'), isNull);
    });

    test('basicBot and strongBot declare no parameters', () {
      expect(builtInBotSpecForCode('basicBot')?.parameters, isEmpty);
      expect(builtInBotSpecForCode('strongBot')?.parameters, isEmpty);
    });

    test('tactician declares a nonnegative strength with default 50', () {
      final tactician = builtInBotSpecForCode('tactician')!;
      expect(tactician.parameters, hasLength(1));
      final strength = tactician.parameters.single;
      expect(strength.name, 'strength');
      expect(strength.type, BotParameterType.integer);
      expect(strength.defaultValue, 50);
      expect(strength.min, 0);
      expect(strength.max, isNull);
      // The schema itself must be valid.
      expect(validateParameterDefinition(strength), isEmpty);
    });
  });

  group('SessionStartMessage params', () {
    test('round-trips params', () {
      const message = SessionStartMessage(
        sessionId: 'session-1',
        params: {'strength': 25},
      );
      final json = message.toJson();
      expect(json['params'], {'strength': 25});
      final decoded = SessionStartMessage.fromJson(json);
      expect(decoded.params, {'strength': 25});
    });

    test('omits params when empty', () {
      const message = SessionStartMessage(sessionId: 'session-1');
      expect(message.toJson().containsKey('params'), isFalse);
    });

    test('tolerates missing params on decode', () {
      final decoded = SessionStartMessage.fromJson(const {'session_id': 's'});
      expect(decoded.params, isNull);
    });
  });

  group('registry DTOs with parameters', () {
    final createdAt = DateTime.utc(2026, 1, 1);

    test('BotDefinition round-trips parameters', () {
      final definition = BotDefinition(
        botDefinitionId: 'definition-1',
        providerId: 'provider-1',
        displayName: 'Tempo Bot',
        version: '1.0.0',
        description: '',
        botCode: 'tempo_bot',
        supportedRuleSets: const ['classic'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        visibility: BotVisibility.private,
        status: BotDefinitionStatus.active,
        createdAt: createdAt,
        updatedAt: createdAt,
        parameters: const [
          BotParameterDefinition(
            name: 'aggressive',
            type: BotParameterType.boolean,
            defaultValue: false,
          ),
        ],
      );
      final json = definition.toJson();
      final decoded = BotDefinition.fromJson(json);
      expect(decoded.parameters, hasLength(1));
      expect(decoded.parameters.single.name, 'aggressive');
      expect(decoded.parameters.single.type, BotParameterType.boolean);
      expect(decoded.parameters.single.defaultValue, false);
    });

    test('BotDefinition omits parameters when empty', () {
      final definition = BotDefinition(
        botDefinitionId: 'definition-1',
        providerId: 'provider-1',
        displayName: 'Plain Bot',
        version: '1.0.0',
        description: '',
        botCode: 'plain_bot',
        supportedRuleSets: const ['classic'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        visibility: BotVisibility.private,
        status: BotDefinitionStatus.active,
        createdAt: createdAt,
        updatedAt: createdAt,
      );
      expect(definition.toJson()['parameters'], isEmpty);
    });

    test('BotDeployment round-trips parameter values', () {
      final deployment = BotDeployment(
        deploymentId: 'deployment-1',
        providerId: 'provider-1',
        transportType: BotTransportType.http,
        baseUrl: Uri.parse('https://bot.example.com/guandan'),
        supportedBotDefinitionIds: const ['definition-1'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        maxConcurrentSessions: 16,
        status: BotDeploymentStatus.healthy,
        createdAt: createdAt,
        updatedAt: createdAt,
        parameterValues: const {'strength': 30},
      );
      final json = deployment.toJson();
      expect(json['parameter_values'], {'strength': 30});
      final decoded = BotDeployment.fromJson(json);
      expect(decoded.parameterValues, {'strength': 30});
    });

    test('BotDeployment omits empty parameter values', () {
      final deployment = BotDeployment(
        deploymentId: 'deployment-1',
        providerId: 'provider-1',
        transportType: BotTransportType.http,
        baseUrl: Uri.parse('https://bot.example.com/guandan'),
        supportedBotDefinitionIds: const ['definition-1'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        maxConcurrentSessions: 16,
        status: BotDeploymentStatus.healthy,
        createdAt: createdAt,
        updatedAt: createdAt,
      );
      expect(deployment.toJson().containsKey('parameter_values'), isFalse);
    });

    test('seat assignments round-trip parameter values', () {
      final deployment = BotDeployment(
        deploymentId: 'deployment-1',
        providerId: 'provider-1',
        transportType: BotTransportType.http,
        baseUrl: Uri.parse('https://bot.example.com/guandan'),
        supportedBotDefinitionIds: const ['definition-1'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        maxConcurrentSessions: 16,
        status: BotDeploymentStatus.healthy,
        createdAt: createdAt,
        updatedAt: createdAt,
      );
      final deployed = DeployedBotSeatAssignment(
        seat: 2,
        playerId: 'player-2',
        botDefinitionId: 'definition-1',
        deployment: deployment,
        parameterValues: const {'strength': 30},
      );
      final deployedJson = deployed.toJson();
      expect(deployedJson['parameter_values'], {'strength': 30});
      expect(
        DeployedBotSeatAssignment.fromJson(deployedJson).parameterValues,
        {'strength': 30},
      );

      const builtIn = BuiltInBotSeatAssignment(
        seat: 3,
        playerId: 'player-3',
        botCode: 'tactician',
        parameterValues: {'strength': 25},
      );
      final builtInJson = builtIn.toJson();
      expect(builtInJson['parameter_values'], {'strength': 25});
      expect(
        BuiltInBotSeatAssignment.fromJson(builtInJson).parameterValues,
        {'strength': 25},
      );
    });

    test('CreateBotDefinitionRequest round-trips parameters', () {
      final request = CreateBotDefinitionRequest(
        providerId: 'provider-1',
        displayName: 'Tempo Bot',
        version: '1.0.0',
        description: '',
        botCode: 'tempo_bot',
        supportedRuleSets: const ['classic'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        parameters: const [
          BotParameterDefinition(
            name: 'mode',
            type: BotParameterType.string,
            defaultValue: 'median',
            choices: ['max', 'median', 'low'],
          ),
        ],
      );
      final decoded = CreateBotDefinitionRequest.fromJson(request.toJson());
      expect(decoded.parameters.single.choices, ['max', 'median', 'low']);
    });

    test('RegisterBotDeploymentRequest round-trips parameter values', () {
      final request = RegisterBotDeploymentRequest(
        providerId: 'provider-1',
        transportType: BotTransportType.http,
        baseUrl: Uri.parse('https://bot.example.com/guandan'),
        supportedBotDefinitionIds: const ['definition-1'],
        supportedProtocolVersions: const ['guandan-bot-v1'],
        maxConcurrentSessions: 16,
        parameterValues: const {'strength': 30},
      );
      final decoded = RegisterBotDeploymentRequest.fromJson(request.toJson());
      expect(decoded.parameterValues, {'strength': 30});
    });
  });

  group('BotSelectionData parameterValues', () {
    test('round-trips parameter values', () {
      final selection = BotSelectionData(
        type: 'builtin',
        botCode: 'tactician',
        parameterValues: const {'strength': 25},
      );
      final json = selection.toJson();
      expect(json['parameter_values'], {'strength': 25});
      expect(
        BotSelectionData.fromJson(json).parameterValues,
        {'strength': 25},
      );
    });

    test('omits empty parameter values', () {
      final selection = BotSelectionData(type: 'builtin', botCode: 'strongBot');
      expect(selection.toJson().containsKey('parameter_values'), isFalse);
    });

    test('tolerates missing parameter values on decode', () {
      final selection = BotSelectionData.fromJson(const {
        'type': 'builtin',
        'bot_code': 'tactician',
      });
      expect(selection.parameterValues, isEmpty);
    });
  });
}
