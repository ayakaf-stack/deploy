import pytest
from app import db, Word, Genre, Word_genre

# ==========================================
# 管理者画面（/admin）の単体テスト
# ==========================================

def test_admin_access_denied_when_not_admin(client):
    """【権限チェック】管理者セッション（is_admin）がない場合、ログイン画面へリダイレクトされるか"""
    response = client.get('/admin', follow_redirects=True)

    assert response.status_code == 200
    assert '管理者としてログインしてください' in response.get_data(as_text=True)


def test_admin_get_success(client, app):
    """【正常系GET】管理者ログイン状態でアクセスした場合、正常にHTML画面が描画されるか"""
    with client.session_transaction() as session:
        session['is_admin'] = True

    response = client.get('/admin')

    assert response.status_code == 200


def test_admin_get_ajax(client, app):
    """【正常系GET / Ajax】XMLHttpRequestヘッダー付きでリクエストした場合、JSONが返るか"""
    with client.session_transaction() as session:
        session['is_admin'] = True

    # Ajaxリクエストを送る
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    response = client.get('/admin', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert 'items' in data
    assert 'genres' in data


import uuid
import pytest
from app import db, Word, Genre, Word_genre

def test_admin_get_filter(client, app):
    """【正常系GET / フィルタ】genre_filter (has / none) で正しく絞り込みが行われるか"""
    # 一意な識別子を生成して重複エラーを回避
    unique_suffix = str(uuid.uuid4())[:8]
    word1_name = f'テスト_あり_{unique_suffix}'
    word2_name = f'テスト_なし_{unique_suffix}'

    word1 = Word(word=word1_name, reading='タンゴエー', mean='意味A')
    word2 = Word(word=word2_name, reading='タンゴビー', mean='意味B')
    genre1 = Genre(genre=f'ジャンル_{unique_suffix}')
    
    db.session.add_all([word1, word2, genre1])
    db.session.commit()

    # word1 にのみジャンルを紐付ける
    db.session.add(Word_genre(word_id=word1.id, genre_id=genre1.id))
    db.session.commit()

    try:
        with client.session_transaction() as session:
            session['is_admin'] = True

        headers = {'X-Requested-With': 'XMLHttpRequest'}

        # 1. genre_filter='has'（ジャンルありのみ）
        res_has = client.get('/admin?genre_filter=has', headers=headers)
        items_has_ids = [item['id'] for item in res_has.get_json()['items']]
        assert word1.id in items_has_ids      # ジャンルありの word1 は含まれる
        assert word2.id not in items_has_ids  # ジャンルなしの word2 は除外される

        # 2. genre_filter='none'（ジャンルなしのみ）
        res_none = client.get('/admin?genre_filter=none', headers=headers)
        items_none_ids = [item['id'] for item in res_none.get_json()['items']]
        assert word1.id not in items_none_ids # ジャンルありの word1 は除外される
        assert word2.id in items_none_ids     # ジャンルなしの word2 は含まれる

    finally:
        # テスト後処理：作成したデータを削除してDBをクリーンに保つ
        Word_genre.query.filter_by(word_id=word1.id).delete()
        db.session.delete(word1)
        db.session.delete(word2)
        db.session.delete(genre1)
        db.session.commit()


import uuid

def test_admin_post_update_genres_success(client, app):
    """【正常系POST】単語に対するジャンルの追加・削除がDBに適用されるか"""
    # 一意な識別子を生成して重複エラーを回避
    unique_suffix = str(uuid.uuid4())[:8]

    word = Word(
        word=f'テスト更新用単語_{unique_suffix}', 
        reading=f'テストコウシンヨウタンゴ_{unique_suffix}', 
        mean='意味'
    )
    g1 = Genre(genre=f'テストジャンル1_{unique_suffix}')
    g2 = Genre(genre=f'テストジャンル2_{unique_suffix}')
    db.session.add_all([word, g1, g2])
    db.session.commit()

    # 最初は g1 だけ追加しておく
    wg1 = Word_genre(word_id=word.id, genre_id=g1.id)
    db.session.add(wg1)
    db.session.commit()

    try:
        with client.session_transaction() as session:
            session['is_admin'] = True

        # POSTで g1 を外し、g2 を新しく割り当てる
        payload = {
            'word_id': word.id,
            'genre_ids': [g2.id]
        }
        response = client.post('/admin', json=payload)

        assert response.status_code == 200
        assert response.get_json().get('success') is True

        # DBの更新結果を検証
        current_genres = Word_genre.query.filter_by(word_id=word.id).all()
        current_genre_ids = {wg.genre_id for wg in current_genres}

        assert g1.id not in current_genre_ids
        assert g2.id in current_genre_ids

    finally:
        # テスト後処理：追加したデータを削除してDBをキレイに保つ
        Word_genre.query.filter_by(word_id=word.id).delete()
        db.session.delete(word)
        db.session.delete(g1)
        db.session.delete(g2)
        db.session.commit()


def test_admin_post_missing_word_id(client, app):
    """【異常系POST】word_idが未指定の場合、400エラーが返るか"""
    with client.session_transaction() as session:
        session['is_admin'] = True

    payload = {
        'genre_ids': [1, 2]
    }
    response = client.post('/admin', json=payload)

    assert response.status_code == 400
    assert response.get_json().get('error') == '単語を選択してください'