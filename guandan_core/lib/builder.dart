import 'package:build/build.dart';
import 'package:source_gen/source_gen.dart';
import 'src/message_helper.dart';

Builder messageUnionBuilder(BuilderOptions options) =>
    LibraryBuilder(MessageUnionGenerator(),
        generatedExtension: '.g.dart');