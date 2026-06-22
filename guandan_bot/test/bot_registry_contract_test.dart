import 'package:guandan_bot/guandan_bot.dart';
import 'package:test/test.dart';

void main() {
  test('bot registration request contracts round-trip JSON', () {
    const providerRequest = RegisterBotProviderRequest(
      displayName: 'Acme Bots',
      contactEmail: 'bots@example.com',
    );
    final definitionRequest = CreateBotDefinitionRequest(
      providerId: 'provider-1',
      displayName: 'Tempo Bot',
      version: '1.0.0',
      description: 'Tempo-oriented bot.',
        botCode: 'test_bot',
      supportedRuleSets: const ['classic'],
      supportedProtocolVersions: const ['guandan-bot-v1'],
      visibility: BotVisibility.public,
    );
    final deploymentRequest = RegisterBotDeploymentRequest(
      providerId: 'provider-1',
      transportType: BotTransportType.http,
      baseUrl: Uri.parse('https://bot.example.com/guandan'),
      supportedBotDefinitionIds: const ['definition-1'],
      supportedProtocolVersions: const ['guandan-bot-v1'],
      maxConcurrentSessions: 16,
      region: 'us-west',
    );

    expect(
      RegisterBotProviderRequest.fromJson(providerRequest.toJson())
          .contactEmail,
      'bots@example.com',
    );
    expect(
      CreateBotDefinitionRequest.fromJson(definitionRequest.toJson())
          .visibility,
      BotVisibility.public,
    );
    expect(
      RegisterBotDeploymentRequest.fromJson(deploymentRequest.toJson())
          .baseUrl
          .toString(),
      'https://bot.example.com/guandan',
    );
  });

  test('bot discovery response round-trips registry entities', () {
    final now = DateTime.utc(2026, 6, 3);
    final response = BotDiscoveryResponse(
      providers: [
        BotProvider(
          providerId: 'provider-1',
          displayName: 'Acme Bots',
          ownerAccountId: 'developer-1',
          contactEmail: 'bots@example.com',
          status: BotProviderStatus.pending,
          createdAt: now,
          updatedAt: now,
        ),
      ],
      definitions: [
        BotDefinition(
          botDefinitionId: 'definition-1',
          providerId: 'provider-1',
          displayName: 'Tempo Bot',
          version: '1.0.0',
          description: 'Tempo bot.',
        botCode: 'test_bot',
          supportedRuleSets: const ['classic'],
          supportedProtocolVersions: const ['guandan-bot-v1'],
          visibility: BotVisibility.public,
          status: BotDefinitionStatus.active,
          createdAt: now,
          updatedAt: now,
        ),
      ],
      deployments: [
        BotDeployment(
          deploymentId: 'deployment-1',
          providerId: 'provider-1',
          transportType: BotTransportType.websocket,
          supportedBotDefinitionIds: const ['definition-1'],
          supportedProtocolVersions: const ['guandan-bot-v1'],
          maxConcurrentSessions: 32,
          status: BotDeploymentStatus.pendingVerification,
          createdAt: now,
          updatedAt: now,
        ),
      ],
    );

    final decoded = BotDiscoveryResponse.fromJson(response.toJson());

    expect(decoded.providers.single.status, BotProviderStatus.pending);
    expect(decoded.definitions.single.botDefinitionId, 'definition-1');
    expect(
        decoded.deployments.single.transportType, BotTransportType.websocket);
  });
}
