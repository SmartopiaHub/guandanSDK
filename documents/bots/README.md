# Bot Development Documentation

This folder contains the public contract for third-party Guandan bot developers.

- `bot_development_spec.md` describes the runtime bot protocol, transport rules,
  message handling, and action response requirements.
- `bot_registration_api.md` describes the lobby REST API for bot discovery,
  provider registration, bot definition publishing, and deployment registration.

All JSON field names use `snake_case`. The shared Dart contracts live in the
`guandan_bot` package and are exported by `package:guandan_bot/guandan_bot.dart`.
