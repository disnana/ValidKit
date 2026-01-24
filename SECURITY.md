# セキュリティポリシー

## サポートされているバージョン

現在、以下のバージョンに対してセキュリティアップデートを提供しています。

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < 1.0   | :x:                |

最新バージョンを使用することを強く推奨します。古いバージョンでは、セキュリティパッチが提供されない場合があります。

---

## 脆弱性の報告

ValidKit のセキュリティ脆弱性を発見された場合は、以下の手順に従って報告してください。

### 報告方法

**機密性の高い脆弱性の場合（推奨）**

GitHub のセキュリティアドバイザリ機能を使用してください。

1. [Security Advisories ページ](https://github.com/disnana/ValidKit/security/advisories)にアクセス
2. "Report a vulnerability" をクリック
3. 脆弱性の詳細を記入して送信

**一般的な問題の場合**

GitHub Issue を作成することもできますが、機密性の高い脆弱性の場合は上記の方法を使用してください。

### 報告に含めるべき情報

脆弱性を報告する際は、以下の情報を含めてください。

- 脆弱性の種類と影響範囲
- 再現手順（可能な限り詳細に）
- 影響を受けるバージョン
- 可能であれば、修正案や回避策
- 概念実証コード（PoC）があれば

### 対応プロセス

1. **確認**：24〜48時間以内に受領確認を送信します

2. **調査**：脆弱性の検証と影響範囲の調査を行います

3. **修正**：脆弱性の重大度に応じて修正作業を開始します

4. **公開**：修正版リリース後、適切な期間を経てセキュリティアドバイザリを公開します

### 重大度の評価

脆弱性は以下の基準で評価されます。

- **Critical**: リモートコード実行、認証バイパスなど
- **High**: データ漏洩、権限昇格など
- **Medium**: サービス拒否、情報開示など
- **Low**: その他のセキュリティ上の懸念

---

## セキュリティアップデートポリシー

### リリースサイクル

- セキュリティパッチは優先的にリリースされます
- 重大な脆弱性の場合、緊急パッチをリリースすることがあります
- セキュリティ修正は GitHub Release と PyPI で公開されます

### 通知

セキュリティアップデートは以下の方法で通知されます。

- GitHub Security Advisories
- GitHub Releases
- README.md のバッジ更新

---

## サプライチェーンセキュリティ

ValidKit は以下のセキュリティ対策を実施しています。

### SLSA Provenance

- すべてのリリースに SLSA v3 準拠の来歴証明（provenance）を付与
- PyPI Trusted Publishing（OIDC）を使用した安全な公開
- GitHub Actions による自動化されたビルドプロセス

### 検証方法

配布物の検証は `slsa-verifier` を使用できます。

```bash
slsa-verifier verify-artifact dist/validkit-*.whl \
  --provenance multiple.intoto.jsonl \
  --source-uri github.com/disnana/ValidKit
```

詳細は [README.md](README.md#サプライチェーンセキュリティ) を参照してください。

---

## 安全な利用のためのベストプラクティス

ValidKit を安全に使用するための推奨事項を以下に示します。

### 1. 最新バージョンの使用

```bash
pip install --upgrade validkit-py
```

定期的に更新を確認し、最新バージョンを使用してください。

### 2. 入力の検証

- 信頼できないソースからの入力は必ずバリデーションを行ってください
- 正規表現を使用する際は、ReDoS（Regular Expression Denial of Service）攻撃に注意してください

### 3. エラーハンドリング

- バリデーションエラーを適切に処理し、機密情報を含むエラーメッセージを外部に公開しないでください

### 4. 依存関係の管理

- ValidKit は最小限の依存関係で設計されていますが、プロジェクト全体の依存関係を定期的に監査してください

### 5. セキュアなスキーマ設計

- 過度に複雑なバリデーションパターンは避け、パフォーマンスとセキュリティのバランスを取ってください

---

## 既知の制限事項

現時点で既知のセキュリティ上の制限事項は以下の通りです。

- ValidKit はバリデーションライブラリであり、サニタイゼーション機能は提供していません
- 非常に大きなデータや深くネストされたデータに対しては、DoS 攻撃のリスクがあります

---

## お問い合わせ

セキュリティに関する質問や懸念事項がある場合は、以下をご利用ください。

- GitHub Security Advisories: [Report a vulnerability](https://github.com/disnana/ValidKit/security/advisories)
- GitHub Issues: [Create an issue](https://github.com/disnana/ValidKit/issues) (非機密情報のみ)

---

## 謝辞

セキュリティ脆弱性を責任を持って報告してくださった方々に感謝いたします。

脆弱性を発見し報告された方は、修正版リリース後に（ご希望があれば）謝辞として記載させていただきます。

---

## 改訂履歴

- 2026-01-24: 初版作成

---
---

# Security Policy

## Supported Versions

The following versions are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < 1.0   | :x:                |

We strongly recommend using the latest version. Older versions may not receive security patches.

---

## Reporting a Vulnerability

If you discover a security vulnerability in ValidKit, please follow these steps:

### How to Report

**For Sensitive Vulnerabilities (Recommended):**

Use GitHub Security Advisories:

1. Visit the [Security Advisories page](https://github.com/disnana/ValidKit/security/advisories)
2. Click "Report a vulnerability"
3. Fill in the details and submit

**For General Issues:**

You can create a GitHub Issue, but please use the above method for sensitive vulnerabilities.

### Information to Include

When reporting a vulnerability, please include:

- Type of vulnerability and its impact
- Steps to reproduce (as detailed as possible)
- Affected versions
- Suggested fix or workaround, if available
- Proof of concept code, if available

### Response Process

1. **Acknowledgment**: We will acknowledge receipt within 24-48 hours

2. **Investigation**: We will verify the vulnerability and assess its impact

3. **Fix**: We will begin remediation based on severity

4. **Disclosure**: After releasing a fix, we will publish a security advisory after an appropriate period

### Severity Assessment

Vulnerabilities will be assessed using the following criteria:

- **Critical**: Remote code execution, authentication bypass, etc.
- **High**: Data leakage, privilege escalation, etc.
- **Medium**: Denial of service, information disclosure, etc.
- **Low**: Other security concerns

---

## Security Update Policy

### Release Cycle

- Security patches are released with high priority
- Critical vulnerabilities may trigger emergency patch releases
- Security fixes are published on GitHub Releases and PyPI

### Notifications

Security updates will be announced through:

- GitHub Security Advisories
- GitHub Releases
- Badge updates in README.md

---

## Supply Chain Security

ValidKit implements the following security measures:

### SLSA Provenance

- All releases include SLSA v3 compliant provenance
- Secure publishing using PyPI Trusted Publishing (OIDC)
- Automated build process via GitHub Actions

### Verification

You can verify distributions using `slsa-verifier`:

```bash
slsa-verifier verify-artifact dist/validkit-*.whl \
  --provenance multiple.intoto.jsonl \
  --source-uri github.com/disnana/ValidKit
```

See [README.md](README.md#サプライチェーンセキュリティ) for more details.

---

## Best Practices for Secure Usage

Recommendations for using ValidKit securely:

### 1. Use Latest Version

```bash
pip install --upgrade validkit-py
```

Regularly check for updates and use the latest version.

### 2. Input Validation

- Always validate input from untrusted sources
- Be cautious of ReDoS attacks when using regular expressions

### 3. Error Handling

- Handle validation errors properly and avoid exposing sensitive information in error messages

### 4. Dependency Management

- ValidKit is designed with minimal dependencies, but regularly audit your project's dependencies

### 5. Secure Schema Design

- Avoid overly complex validation patterns and balance performance with security

---

## Known Limitations

Known security limitations at this time:

- ValidKit is a validation library and does not provide sanitization features
- Very large or deeply nested data may pose DoS attack risks

---

## Contact

For security-related questions or concerns:

- GitHub Security Advisories: [Report a vulnerability](https://github.com/disnana/ValidKit/security/advisories)
- GitHub Issues: [Create an issue](https://github.com/disnana/ValidKit/issues) (non-sensitive only)

---

## Acknowledgments

We thank those who responsibly disclose security vulnerabilities to us.

Researchers who discover and report vulnerabilities will be acknowledged (if desired) after the fix is released.

---

## Revision History

- 2026-01-24: Initial version created
