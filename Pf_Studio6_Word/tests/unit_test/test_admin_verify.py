import pytest
from unittest.mock import patch
from itsdangerous import SignatureExpired

# ==========================================
# 管理者マジックリンク検証（/admin/verify/<token>）の単体テスト
# ==========================================

def test_admin_verify_success(client, app):
    """【正常系】正しいトークンでアクセスした場合、管理者ログインが完了し管理者ページへアクセスできるか"""
    from app import serializer, ADMIN_EMAIL, used_tokens

    # 1. テスト用の有効なトークンを生成
    token = serializer.dumps(ADMIN_EMAIL, salt='admin-login')

    # 2. リクエスト送信
    response = client.get(f'/admin/verify/{token}', follow_redirects=True)

    # 3. 検証
    # セッションに is_admin フラグが立っているか
    with client.session_transaction() as session:
        assert session.get('is_admin') is True

    # used_tokens に追加されたか
    assert token in used_tokens

    # フラッシュメッセージが表示されたか
    assert '管理者としてログインしました' in response.get_data(as_text=True)


def test_admin_verify_used_token(client, app):
    """【異常系】使用済みのトークンでアクセスした場合、拒否されるか"""
    from app import serializer, ADMIN_EMAIL, used_tokens

    token = serializer.dumps(ADMIN_EMAIL, salt='admin-login')

    # 事前に使用済みセットへ追加
    used_tokens.add(token)

    response = client.get(f'/admin/verify/{token}', follow_redirects=True)

    # エラーメッセージの検証
    assert 'このリンクは既に使用されています' in response.get_data(as_text=True)


def test_admin_verify_expired_token(client, app):
    """【異常系】有効期限（15分）が切れたトークンの場合、拒否されるか"""
    from app import serializer, ADMIN_EMAIL

    # 他のテストと重複しない新しいトークン文字列を用意
    expired_token = "expired-dummy-token-string"

    # loads が呼ばれたときに SignatureExpired 例外を発生させる
    with patch.object(serializer, 'loads', side_effect=SignatureExpired('Signature expired')):
        response = client.get(f'/admin/verify/{expired_token}', follow_redirects=True)

    # エラーメッセージの検証
    assert 'リンクの有効期限が切れています' in response.get_data(as_text=True)


def test_admin_verify_invalid_token(client, app):
    """【異常系】改ざんされた不正なトークンの場合、拒否されるか"""
    invalid_token = "invalid-token-string-12345"

    response = client.get(f'/admin/verify/{invalid_token}', follow_redirects=True)

    # エラーメッセージの検証
    assert '不正なリンクです' in response.get_data(as_text=True)