// dart format width=80
// GENERATED CODE - DO NOT MODIFY BY HAND

// **************************************************************************
// MessageUnionGenerator
// **************************************************************************

part of 'message.dart';

class GameMessageFactory {
  static GameMessage fromJson(Map<String, dynamic> json) {
    final msgType = MessageType.from(json["type"]);
    switch (msgType) {
      case MessageType.iNewRound:
        return NewRoundMessage.fromJson(json);
      case MessageType.iNewPhase:
        return NewPhaseMessage.fromJson(json);
      case MessageType.iStartPlayer:
        return StartPlayerMessage.fromJson(json);
      case MessageType.iHandPlayed:
        return HandPlayedMessage.fromJson(json);
      case MessageType.iTributeResult:
        return TributeResultMessage.fromJson(json);
      case MessageType.sPlayHandRequest:
        return ServerPlayHandRequest.fromJson(json);
      case MessageType.sTributeCardRequest:
        return ServerTributeRequest.fromJson(json);
      case MessageType.sReturnCardRequest:
        return ServerReturnCardRequest.fromJson(json);
      case MessageType.pJoinRoomRequest:
        return JoinRoomRequest.fromJson(json);
      case MessageType.pQuitRoomRequest:
        return QuitRoomRequest.fromJson(json);
      case MessageType.pPlayHandRequest:
        return PlayerPlayHandRequest.fromJson(json);
      case MessageType.pPayTributeRequest:
        return PlayerPayTributeRequest.fromJson(json);
      case MessageType.pReturnCardRequest:
        return PlayerReturnCardRequest.fromJson(json);
      case MessageType.pNewRoundRequest:
        return NewRoundRequest.fromJson(json);
      case MessageType.pStartGameRequest:
        return StartGameRequest.fromJson(json);
      case MessageType.pCreateRoomRequest:
        return CreateRoomRequest.fromJson(json);
      case MessageType.iRoomOwner:
        return RoomOwnerMessage.fromJson(json);
      case MessageType.iPlayerJoinedRoom:
        return PlayerJoinedRoomMessage.fromJson(json);
      case MessageType.iPlayerQuitRoom:
        return PlayerQuitRoomMessage.fromJson(json);
      case MessageType.iRequestResult:
        return RequestResultMessage.fromJson(json);
      case MessageType.iMoreTimeGranted:
        return MoreTimeGrantedMessage.fromJson(json);
      case MessageType.autoDelegated:
        return AutoDelegationMessage.fromJson(json);
      case MessageType.iPlayerSeat:
        return PlayerSeatMessage.fromJson(json);
      case MessageType.iGameRoomClosed:
        return GameRoomClosedMessage.fromJson(json);
      case MessageType.iJieFeng:
        return JieFengMessage.fromJson(json);
      case MessageType.iTeamScores:
        return TeamScoresMessage.fromJson(json);
      case MessageType.iPlayerEmptiedHand:
        return PlayerEmptiedHandMessage.fromJson(json);
      case MessageType.iRoundResult:
        return RoundResultMessage.fromJson(json);
      case MessageType.iCardsOnHand:
        return CardsOnHandMessage.fromJson(json);
      case MessageType.iPlayerRemovedFromRoom:
        return PlayerRemovedMessage.fromJson(json);
      case MessageType.iTimeOut:
        return PlayerTimeoutMessage.fromJson(json);
      case MessageType.iTributeCard:
        return TributeCardMessage.fromJson(json);
      case MessageType.iReturnCard:
        return ReturnCardMessage.fromJson(json);
      case MessageType.iTributeResistance:
        return TributeResistanceMessage.fromJson(json);
      case MessageType.iGameRoomCreated:
        return GameRoomCreatedMessage.fromJson(json);
      case MessageType.heartbeat:
        return HeartbeatMessage.fromJson(json);
      case MessageType.pMoreTimeRequest:
        return MoreTimeRequest.fromJson(json);
      case MessageType.pSeatRequest:
        return SeatRequest.fromJson(json);
      case MessageType.iServerClosed:
        return ServerClosedMessage.fromJson(json);
      case MessageType.iRoundEnded:
        return RoundEndedMessage.fromJson(json);
      default:
        throw UnsupportedError("Unknown type: ${json["type"]}");
    }
  }
}
