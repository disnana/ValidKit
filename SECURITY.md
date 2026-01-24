# セキュリティポリシー / Security Policy

## サポートされているバージョン / Supported Versions

現在、以下のバージョンに対してセキュリティアップデートを提供しています。

The following versions are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < 1.0   | :x:                |

最新バージョンを使用することを強く推奨します。古いバージョンでは、セキュリティパッチが提供されない場合があります。

We strongly recommend using the latest version. Older versions may not receive security patches.

---

## 脆弱性の報告 / Reporting a Vulnerability

ValidKit のセキュリティ脆弱性を発見された場合は、以下の手順に従って報告してください。

If you discover a security vulnerability in ValidKit, please follow these steps:

### 報告方法 / How to Report

**機密性の高い脆弱性の場合（推奨）/ For Sensitive Vulnerabilities (Recommended):**

GitHub のセキュリティアドバイザリ機能を使用してください：

1. [Security Advisories ページ](https://github.com/disnana/ValidKit/security/advisories)にアクセス
2. "Report a vulnerability" をクリック
3. 脆弱性の詳細を記入して送信

Use GitHub Security Advisories:

1. Visit the [Security Advisories page](https://github.com/disnana/ValidKit/security/advisories)
2. Click "Report a vulnerability"
3. Fill in the details and submit

**一般的な問題の場合 / For General Issues:**

GitHub Issue を作成することもできますが、機密性の高い脆弱性の場合は上記の方法を使用してください。

You can create a GitHub Issue, but please use the above method for sensitive vulnerabilities.

### 報告に含めるべき情報 / Information to Include

脆弱性を報告する際は、以下の情報を含めてください：

When reporting a vulnerability, please include:

- 脆弱性の種類と影響範囲 / Type of vulnerability and its impact
- 再現手順（可能な限り詳細に）/ Steps to reproduce (as detailed as possible)
- 影響を受けるバージョン / Affected versions
- 可能であれば、修正案や回避策 / Suggested fix or workaround, if available
- 概念実証コード（PoC）があれば / Proof of concept code, if available

### 対応プロセス / Response Process

1. **確認**：24〜48時間以内に受領確認を送信します
   - **Acknowledgment**: We will acknowledge receipt within 24-48 hours

2. **調査**：脆弱性の検証と影響範囲の調査を行います
   - **Investigation**: We will verify the vulnerability and assess its impact

3. **修正**：脆弱性の重大度に応じて修正作業を開始します
   - **Fix**: We will begin remediation based on severity

4. **公開**：修正版リリース後、適切な期間を経てセキュリティアドバイザリを公開します
   - **Disclosure**: After releasing a fix, we will publish a security advisory after an appropriate period

### 重大度の評価 / Severity Assessment

脆弱性は以下の基準で評価されます：

Vulnerabilities will be assessed using the following criteria:

- **Critical**: リモートコード実行、認証バイパスなど
  - Remote code execution, authentication bypass, etc.
  
- **High**: データ漏洩、権限昇格など
  - Data leakage, privilege escalation, etc.
  
- **Medium**: サービス拒否、情報開示など
  - Denial of service, information disclosure, etc.
  
- **Low**: その他のセキュリティ上の懸念
  - Other security concerns

---

## セキュリティアップデートポリシー / Security Update Policy

### リリースサイクル / Release Cycle

- セキュリティパッチは優先的にリリースされます
  - Security patches are released with high priority
  
- 重大な脆弱性の場合、緊急パッチをリリースすることがあります
  - Critical vulnerabilities may trigger emergency patch releases
  
- セキュリティ修正は GitHub Release と PyPI で公開されます
  - Security fixes are published on GitHub Releases and PyPI

### 通知 / Notifications

セキュリティアップデートは以下の方法で通知されます：

Security updates will be announced through:

- GitHub Security Advisories
- GitHub Releases
- README.md のバッジ更新 / Badge updates in README.md

---

## サプライチェーンセキュリティ / Supply Chain Security

ValidKit は以下のセキュリティ対策を実施しています：

ValidKit implements the following security measures:

### SLSA Provenance

- すべてのリリースに SLSA v3 準拠の来歴証明（provenance）を付与
  - All releases include SLSA v3 compliant provenance
  
- PyPI Trusted Publishing（OIDC）を使用した安全な公開
  - Secure publishing using PyPI Trusted Publishing (OIDC)
  
- GitHub Actions による自動化されたビルドプロセス
  - Automated build process via GitHub Actions

### 検証方法 / Verification

配布物の検証は `slsa-verifier` を使用できます：

You can verify distributions using `slsa-verifier`:

```bash
slsa-verifier verify-artifact dist/validkit-*.whl \
  --provenance multiple.intoto.jsonl \
  --source-uri github.com/disnana/ValidKit
```

詳細は [README.md](README.md#サプライチェーンセキュリティ) を参照してください。

See [README.md](README.md#サプライチェーンセキュリティ) for more details.

---

## 安全な利用のためのベストプラクティス / Best Practices for Secure Usage

ValidKit を安全に使用するための推奨事項：

Recommendations for using ValidKit securely:

### 1. 最新バージョンの使用 / Use Latest Version

```bash
pip install --upgrade validkit-py
```

定期的に更新を確認し、最新バージョンを使用してください。

Regularly check for updates and use the latest version.

### 2. 入力の検証 / Input Validation

- 信頼できないソースからの入力は必ずバリデーションを行ってください
  - Always validate input from untrusted sources
  
- 正規表現を使用する際は、ReDoS（Regular Expression Denial of Service）攻撃に注意してください
  - Be cautious of ReDoS attacks when using regular expressions

### 3. エラーハンドリング / Error Handling

- バリデーションエラーを適切に処理し、機密情報を含むエラーメッセージを外部に公開しないでください
  - Handle validation errors properly and avoid exposing sensitive information in error messages

### 4. 依存関係の管理 / Dependency Management

- ValidKit は最小限の依存関係で設計されていますが、プロジェクト全体の依存関係を定期的に監査してください
  - ValidKit is designed with minimal dependencies, but regularly audit your project's dependencies

### 5. セキュアなスキーマ設計 / Secure Schema Design

- 過度に複雑なバリデーションパターンは避け、パフォーマンスとセキュリティのバランスを取ってください
  - Avoid overly complex validation patterns and balance performance with security

---

## 既知の制限事項 / Known Limitations

現時点で既知のセキュリティ上の制限事項：

Known security limitations at this time:

- ValidKit はバリデーションライブラリであり、サニタイゼーション機能は提供していません
  - ValidKit is a validation library and does not provide sanitization features
  
- 非常に大きなデータや深くネストされたデータに対しては、DoS 攻撃のリスクがあります
  - Very large or deeply nested data may pose DoS attack risks

---

## お問い合わせ / Contact

セキュリティに関する質問や懸念事項がある場合：

For security-related questions or concerns:

- GitHub Security Advisories: [Report a vulnerability](https://github.com/disnana/ValidKit/security/advisories)
- GitHub Issues: [Create an issue](https://github.com/disnana/ValidKit/issues) (非機密情報のみ / non-sensitive only)

---

## 謝辞 / Acknowledgments

セキュリティ脆弱性を責任を持って報告してくださった方々に感謝いたします。

We thank those who responsibly disclose security vulnerabilities to us.

脆弱性を発見し報告された方は、修正版リリース後に（ご希望があれば）謝辞として記載させていただきます。

Researchers who discover and report vulnerabilities will be acknowledged (if desired) after the fix is released.

---

## 改訂履歴 / Revision History

- 2026-01-24: 初版作成 / Initial version created
