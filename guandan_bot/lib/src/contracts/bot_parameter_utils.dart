/// Pure helpers for bot parameter schema validation and effective-value
/// resolution. Used by the lobby server (definition/deployment validation and
/// room/benchmark merge), the game server (defensive fallback), and tests.
library;

import 'bot_parameter_contract.dart';

/// The result of resolving parameter values against a schema.
class ParameterResolution {
  const ParameterResolution({required this.effective, required this.errors});

  /// The merged effective values (definition defaults overlaid by deployment
  /// values, overlaid by seat values). Only contains schema-known parameters
  /// whose values validated.
  final Map<String, Object?> effective;

  /// Human-readable validation errors; empty when the merge is valid.
  final List<String> errors;

  bool get isValid => errors.isEmpty;
}

/// Resolves the effective parameter values for a bot instance.
///
/// Precedence (each layer validated against the schema):
/// `definition default < deployment values < seat values`.
/// Values with an unknown name or a wrong type / out-of-constraints value are
/// reported in [ParameterResolution.errors] and excluded from the effective
/// map.
ParameterResolution resolveEffectiveParameters({
  required List<BotParameterDefinition> schema,
  Map<String, Object?> deploymentValues = const {},
  Map<String, Object?> seatValues = const {},
}) {
  final effective = <String, Object?>{};
  final errors = <String>[];
  final byName = {for (final d in schema) d.name: d};

  // Layer 1: definition defaults.
  for (final d in schema) {
    if (d.defaultValue != null) effective[d.name] = d.defaultValue;
  }

  // Layer 2: deployment values.
  for (final entry in deploymentValues.entries) {
    final d = byName[entry.key];
    if (d == null) {
      errors.add("unknown parameter '${entry.key}'");
      continue;
    }
    final error = validateParameterValue(d, entry.value);
    if (error != null) {
      errors.add("parameter '${entry.key}': $error");
      continue;
    }
    effective[entry.key] = entry.value;
  }

  // Layer 3: seat values.
  for (final entry in seatValues.entries) {
    final d = byName[entry.key];
    if (d == null) {
      errors.add("unknown parameter '${entry.key}'");
      continue;
    }
    final error = validateParameterValue(d, entry.value);
    if (error != null) {
      errors.add("parameter '${entry.key}': $error");
      continue;
    }
    effective[entry.key] = entry.value;
  }

  return ParameterResolution(effective: effective, errors: errors);
}

/// Validates one parameter definition. Returns a human-readable error list
/// (empty when the definition is valid).
List<String> validateParameterDefinition(BotParameterDefinition d) {
  final errors = <String>[];
  if (d.name.isEmpty) {
    errors.add('parameter name must not be empty');
  }
  switch (d.type) {
    case BotParameterType.integer:
      if (d.min != null && d.max != null && d.min! > d.max!) {
        errors.add("parameter '${d.name}': min must be <= max");
      }
      if (d.choices != null) {
        errors.add(
            "parameter '${d.name}': choices are only valid for string parameters");
      }
      if (d.defaultValue != null && d.defaultValue is! int) {
        errors.add("parameter '${d.name}': default must be an integer");
      }
      break;
    case BotParameterType.boolean:
      if (d.min != null || d.max != null || d.choices != null) {
        errors.add(
            "parameter '${d.name}': constraints are not valid for boolean parameters");
      }
      if (d.defaultValue != null && d.defaultValue is! bool) {
        errors.add("parameter '${d.name}': default must be a boolean");
      }
      break;
    case BotParameterType.string:
      if (d.min != null || d.max != null) {
        errors.add(
            "parameter '${d.name}': min/max are only valid for integer parameters");
      }
      if (d.choices != null && d.choices!.isEmpty) {
        errors.add("parameter '${d.name}': choices must not be empty");
      }
      if (d.defaultValue != null && d.defaultValue is! String) {
        errors.add("parameter '${d.name}': default must be a string");
      }
      break;
  }
  // The default must itself satisfy the constraints.
  if (d.defaultValue != null) {
    final valueError = validateParameterValue(d, d.defaultValue);
    if (valueError != null) {
      errors.add("parameter '${d.name}': default $valueError");
    }
  }
  return errors;
}

/// Validates one value against a parameter definition. Returns a
/// human-readable error, or null when the value is acceptable.
String? validateParameterValue(BotParameterDefinition d, Object? value) {
  switch (d.type) {
    case BotParameterType.integer:
      if (value is! int) return 'must be an integer';
      if (d.min != null && value < d.min!) return 'must be >= ${d.min}';
      if (d.max != null && value > d.max!) return 'must be <= ${d.max}';
      return null;
    case BotParameterType.boolean:
      if (value is! bool) return 'must be a boolean';
      return null;
    case BotParameterType.string:
      if (value is! String) return 'must be a string';
      if (d.choices != null && !d.choices!.contains(value)) {
        return 'must be one of ${d.choices!.join(', ')}';
      }
      return null;
  }
}
