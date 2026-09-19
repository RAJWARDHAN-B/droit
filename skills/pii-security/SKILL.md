# PII Security Skill

Use for anonymization, de-anonymization, encryption, or document retrieval changes.

1. Default all generated context and responses to aliases.
2. Require an explicit authenticated role for restoration.
3. Record an audit event without storing original values in event details.
4. Keep encryption keys outside source control and use `SecretStr` for configuration.
5. Test repeated values, ambiguous aliases across documents, unauthorized reveals, and audit records.

Never log original PII or decrypted mapping values.
