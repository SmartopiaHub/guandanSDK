// lib/src/message_generator.dart
import 'package:guandan_core/src/message.dart';
import 'package:source_gen/source_gen.dart';
import 'package:build/build.dart';
import 'dart:async';



class MessageUnionGenerator extends Generator {
  @override
  FutureOr<String> generate(LibraryReader library, BuildStep buildStep) {
    final buffer = StringBuffer();
    final annotated = library.annotatedWith(typeChecker);
    buffer.writeln("part of 'message.dart';");
    buffer.writeln('class GameMessageFactory {');
    buffer.writeln('  static GameMessage fromJson(Map<String, dynamic> json) {');
    buffer.writeln('    final msgType = MessageType.from(json["type"]);');
    buffer.writeln('    switch (msgType) {');

    for (var annotation in annotated) {
      final element = annotation.element;
      final className = element.displayName;
      final type = annotation.annotation
          .peek('type')?.revive().accessor;

      if (type != null) {
        buffer.writeln(
            '      case $type: return $className.fromJson(json);');
      }
    }

    buffer.writeln(
        '      default: throw UnsupportedError("Unknown type: \${json["type"]}");');
    buffer.writeln('    }');
    buffer.writeln('  }');
    buffer.writeln('}');

    return buffer.toString();
  }

  final typeChecker = TypeChecker.typeNamed(MsgAnnotation);
}
