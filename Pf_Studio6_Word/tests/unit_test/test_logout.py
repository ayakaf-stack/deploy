# ==========================================
# ログアウト機能（/logout）の単体テスト
# ==========================================

def test_logout_success(client):
    """【正常系】ログイン状態でPOSTリクエストを送るとセッションが破棄されログアウトできるか"""
    # 1. 事前にセッションへ user_id をセット（ログイン状態を模倣）
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['user_name'] = 'テストユーザー'

    # 2. ログアウト処理を実行 (POSTリクエスト)
    response = client.post('/logout', follow_redirects=True)

    # 3. 検証: セッションから user_id が消えているか
    with client.session_transaction() as session:
        assert 'user_id' not in session
        assert 'user_name' not in session

    # フラッシュメッセージとリダイレクト結果の検証
    assert response.status_code == 200
    assert 'ログアウトしました' in response.get_data(as_text=True)


def test_logout_when_not_logged_in(client):
    """【境界値】未ログイン状態でPOSTリクエストを送っても正常にトップページへ転送されるか"""
    # ログインせずに POST リクエストを送信
    response = client.post('/logout', follow_redirects=True)

    # セッションが空のままであり、エラーにならず200でレスポンスが返るか
    assert response.status_code == 200
    # 未ログイン時は flash メッセージが出ないため、ログアウト文言が含まれないことを確認
    assert 'ログアウトしました' not in response.get_data(as_text=True)


def test_logout_method_not_allowed(client):
    """【異常系】GETリクエストでアクセスした場合に405エラーになるか"""
    response = client.get('/logout')

    # GETメソッドは許可されていないため 405 Method Not Allowed
    assert response.status_code == 405