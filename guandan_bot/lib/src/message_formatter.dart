import 'package:guandan_core/guandan_core.dart';

import 'contracts/bot_protocol_contract.dart';

/// Formats [BotMessage] instances into concise, human-readable log strings.
///
/// For [GameMessageEnvelope], the inner [GameMessage] payload is formatted
/// according to its specific subtype (as defined in [GameMessage]), highlighting
/// the most relevant fields for debugging and observability.
class MessageFormatter {
  MessageFormatter._();

  /// Returns a one-line representation of [message] suitable for logging.
  static String format(BotMessage message) {
    return switch (message) {
      SessionStartMessage(
        :final sessionId,
        :final deploymentId,
        :final playerId,
        :final seat,
      ) =>
        'SessionStart(sid=$sessionId, dep=${deploymentId ?? '-'}, '
            'player=${playerId ?? '-'}, seat=${seat ?? '-'})',
      SessionStartedMessage(:final sessionId, :final accepted) =>
        'SessionStarted(sid=$sessionId, accepted=$accepted)',
      SessionEndMessage(:final sessionId) => 'SessionEnd(sid=$sessionId)',
      SessionEndedMessage(:final sessionId) =>
        'SessionEnded(sid=$sessionId)',
      BotErrorMessage(:final sessionId, :final code, :final message) =>
        'Error(sid=$sessionId, code=$code, msg=$message)',
      GameMessageEnvelope(
        :final sessionId,
        :final requestId,
        :final payload,
      ) =>
        'GameMsg(sid=$sessionId, rid=${requestId ?? '-'}) '
            '→ ${_formatGameMessage(payload)}',
    };
  }

  /// Formats the inner [GameMessage] payload according to its subtype.
  static String _formatGameMessage(GameMessage message) {
    return switch (message) {
      // --- Server requests to player ---
      ServerPlayHandRequest(
        :final playerId,
        :final handOnTable,
        :final levelRank,
        :final availableCards,
      ) =>
        'ServerPlayHand(player=$playerId, onTable=${_handStr(handOnTable)}, '
            'level=${levelRank.name}, '
            'cards=${availableCards?.length ?? 0})',
      ServerTributeRequest(:final playerId, :final availableCards) =>
        'ServerTribute(player=$playerId, '
            'cards=${availableCards?.length ?? 0})',
      ServerReturnCardRequest(:final playerId, :final availableCards) =>
        'ServerReturnCard(player=$playerId, '
            'cards=${availableCards?.length ?? 0})',

      // --- Player actions ---
      PlayerPlayHandRequest(:final playerId, :final cards) =>
        'PlayHand(player=$playerId, cards=${cards.length}: $cards)',
      PlayerPayTributeRequest(:final playerId, :final tribute) =>
        'PayTribute(player=$playerId, card=$tribute)',
      PlayerReturnCardRequest(:final playerId, :final returnCard) =>
        'ReturnCard(player=$playerId, card=$returnCard)',
      JoinRoomRequest(:final playerId, :final roomId) =>
        'JoinRoom(player=$playerId, room=$roomId)',
      QuitRoomRequest(:final playerId) =>
        'LeaveRoom(player=$playerId)',
      NewRoundRequest(:final playerId) =>
        'StartRound(player=$playerId)',
      StartGameRequest(:final playerId) =>
        'StartGame(player=$playerId)',
      CreateRoomRequest(
        :final playerId,
        :final roomName,
      ) =>
        'CreateRoom(player=$playerId, name=$roomName)',
      SeatRequest(:final playerId, :final newSeat) =>
        'ChangeSeat(player=$playerId, seat=$newSeat)',
      ExtraTimeRequest(:final playerId, :final seconds) =>
        'MoreTime(player=$playerId, secs=${seconds ?? '-'})',

      // --- Informational messages ---
      NewRoundMessage(
        :final roundId,
        :final levelRank,
        :final hand,
        :final players,
      ) =>
        'NewRound(round=$roundId, level=${levelRank.name}, '
            'players=${players.length}, hand=${hand.length})',
      NewPhaseMessage(:final phaseId, :final startPlayerId) =>
        'NewPhase(phase=$phaseId, start=$startPlayerId)',
      StartPlayerMessage(:final startPlayerId) =>
        'StartPlayer(player=$startPlayerId)',
      HandPlayedMessage(
        :final playerId,
        :final cards,
        :final roundId,
        :final phaseId,
      ) =>
        'HandPlayed(player=$playerId, round=$roundId, phase=$phaseId, '
            'cards=${cards.length}: $cards)',
      TributeResultMessage(:final tributeResult, :final roundId) =>
        'TributeResult(round=$roundId, '
            'resisted=${tributeResult.isResisted}, '
            'tributes=${tributeResult.tributes.length})',
      TributeCardMessage(:final payerId, :final tribute, :final winnerId) =>
        'TributePaid(payer=$payerId, winner=${winnerId ?? '-'}, '
            'card=$tribute)',
      ReturnCardMessage(
        :final payerId,
        :final returnCard,
        :final winnerId,
      ) =>
        'ReturnCardPaid(payer=$payerId, winner=$winnerId, '
            'card=$returnCard)',
      TributeResistanceMessage(:final startPlayerId, :final redJokerCounts) =>
        'TributeResistance(start=$startPlayerId, '
            'redJokers=$redJokerCounts)',
      RoundEndedMessage(:final roundId) => 'RoundEnded(round=$roundId)',
      RoundResultMessage(:final roundResult, :final isPartial) =>
        'RoundResult(banker=${roundResult.banker?.id ?? '-'}, '
            'partial=$isPartial)',
      GameRoomCreatedMessage(:final roomInfo) =>
        'RoomCreated(room=${roomInfo.roomId})',
      GameRoomClosedMessage(:final roomId) => 'RoomClosed(room=$roomId)',
      PlayerJoinedRoomMessage(:final player, :final botCode) =>
        'PlayerJoined(player=${player.id}, '
            'name=${player.name}, seat=${player.seat}, '
            'bot=${botCode ?? '-'})',
      PlayerQuitRoomMessage(:final playerId) =>
        'PlayerLeft(player=$playerId)',
      PlayerSeatMessage(
        :final playerId,
        :final seat,
        :final team,
      ) =>
        'PlayerSeat(player=$playerId, seat=$seat, team=${team.name})',
      PlayerEmptiedHandMessage(:final playerId, playerRank:final rankOfPlayer) =>
        'PlayerEmpty(player=$playerId, rank=${rankOfPlayer.name})',
      PlayerRemovedMessage(:final playerId, :final reason) =>
        'PlayerRemoved(player=$playerId, reason=${reason?.name ?? '-'})',
      CardsOnHandMessage(:final cardsOnHand) =>
        'CardsOnHand(${cardsOnHand.entries
            .map((e) => '${e.key}:${e.value?.length ?? 0}')
            .join(', ')})',
      TeamScoresMessage(:final scores) =>
        'TeamScores(red=${scores.redTeamScore}, '
            'blue=${scores.blueTeamScore})',
      JieFengMessage(:final playerId, :final phaseId) =>
        'JieFeng(player=$playerId, phase=$phaseId)',
      MoreTimeGrantedMessage(
        :final playerId,
        :final newAllocatedSeconds,
      ) =>
        'MoreTimeGranted(player=$playerId, secs=$newAllocatedSeconds)',
      AutoDelegationMessage(:final playerId, :final autoDelegated) =>
        'AutoDelegate(player=$playerId, on=$autoDelegated)',
      PlayerTimeoutMessage(:final playerId, :final request) =>
        'PlayerTimeout(player=$playerId, request=${request.name})',
      RequestResultMessage(
        :final request,
        :final result,
        :final playerId,
      ) =>
        'RequestResult(request=${request?.name}, '
            'result=${result.name}, player=${playerId ?? '-'})',
      RoomOwnerMessage(:final ownerId) => 'RoomOwner(owner=$ownerId)',
      HeartbeatMessage(:final playerId) => 'Heartbeat(player=$playerId)',
      ServerClosedMessage(:final reason) =>
        'ServerClosed(reason=${reason ?? '-'})',

      // Fallback for GameMessage / GameRoomMessage base types
      GameRoomMessage(:final type, :final roomId) =>
        'GameRoomMsg(type=${type.name}, room=$roomId)',
      GameMessage(:final type) => 'GameMsg(type=${type.name})',
    };
  }

  /// Returns a short representation of [hand], or "pass" if empty.
  static String _handStr(Hand hand) {
    if (hand.isEmpty) return 'pass';
    return '${hand.length}: $hand';
  }
}
