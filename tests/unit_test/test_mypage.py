import uuid
import pytest
from app import db
from models.models import User, Word, Text, Good_word, Good_text

def test_mypage_access_denied_when_not_logged_in(client):
    """【異常系】未ログイン時にマイページにアクセスするとログイン画面にリダイレクトされ、フラッシュメッセージが表示されるか"""
    # 1. リダイレクト自体のステータスコードを検証 (302)
    response = client.get('/mypage')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

    # 2. リダイレクト先まで自動で追跡してフラッシュメッセージを検証
    response_followed = client.get('/mypage', follow_redirects=True)
    assert response_followed.status_code == 200

    html = response_followed.get_data(as_text=True)
    assert 'ログインが必要です' in html


def test_mypage_success(client, app):
    """【正常系】ログインユーザーのマイページが正しく表示され、いいね情報・自分の投稿が渡されるか"""
    unique_suffix = str(uuid.uuid4())[:8]

    # 1. テスト用ユーザーの作成（user_name に修正）
    user = User(
        user_name=f'mypage_user_{unique_suffix}',
        email=f'user_{unique_suffix}@example.com',
        password_hash='hashed_password_sample'
    )
    other_user = User(
        user_name=f'other_user_{unique_suffix}',
        email=f'other_{unique_suffix}@example.com',
        password_hash='hashed_password_sample'
    )
    db.session.add_all([user, other_user])
    db.session.commit()

    # 2. テスト用単語・文章の作成
    word = Word(
        word=f'マイページ単語_{unique_suffix}',
        reading='マイページタンゴ',
        mean='意味'
    )
    db.session.add(word)
    db.session.commit()

    text_liked = Text(
        user_id=other_user.id,
        title=f'いいねした文章_{unique_suffix}',
        main_text='テスト本文（いいね用）',
        text_status=0,
        word=word.id
    )
    text_my = Text(
        user_id=user.id,
        title=f'自分の文章_{unique_suffix}',
        main_text='テスト本文（自分の文章用）',
        text_status=0,
        word=word.id
    )
    db.session.add_all([text_liked, text_my])
    db.session.commit()

    # 3. いいねデータの作成
    gw = Good_word(user_id=user.id, word_id=word.id)
    gt = Good_text(user_id=user.id, text_id=text_liked.id)
    # 自分の文章に対する他者からのいいね
    gt_my_text = Good_text(user_id=other_user.id, text_id=text_my.id)
    db.session.add_all([gw, gt, gt_my_text])
    db.session.commit()

    try:
        # 4. セッションにログイン情報をセット
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['user_name'] = user.user_name

        # 5. GET /mypage リクエスト
        response = client.get('/mypage')

        assert response.status_code == 200

        # HTMLレスポンス内に作成したデータが含まれているか検証
        html = response.get_data(as_text=True)
        assert user.user_name in html
        assert word.word in html
        assert text_liked.title in html
        assert text_my.title in html

    finally:
        # テスト後処理：作成したデータを削除
        Good_word.query.filter_by(user_id=user.id).delete()
        Good_text.query.filter_by(user_id=user.id).delete()
        Good_text.query.filter_by(text_id=text_my.id).delete()
        Text.query.filter_by(user_id=user.id).delete()
        Text.query.filter_by(user_id=other_user.id).delete()
        Word.query.filter_by(id=word.id).delete()
        User.query.filter_by(id=user.id).delete()
        User.query.filter_by(id=other_user.id).delete()
        db.session.commit()

def test_mypage_success_with_empty_data(client):
    """【正常系・境界値】いいねや自分の投稿が0件の状態でマイページが正常表示され、未登録メッセージが表示されるか"""
    unique_suffix = str(uuid.uuid4())[:8]

    user = User(
        user_name=f'empty_user_{unique_suffix}',
        email=f'empty_{unique_suffix}@example.com',
        password_hash='hashed_password_sample'
    )
    db.session.add(user)
    db.session.commit()

    try:
        with client.session_transaction() as session:
            session['user_id'] = user.id

        response = client.get('/mypage')
        assert response.status_code == 200

        # HTMLレスポンスを取得して0件時のメッセージが含まれているか検証
        html = response.get_data(as_text=True)
        assert 'まだいいねした単語はありません' in html
        assert 'まだいいねした文章はありません' in html
        assert 'まだ作成した文章はありません' in html

    finally:
        User.query.filter_by(id=user.id).delete()
        db.session.commit()


def test_mypage_user_not_found(client):
    """【異常系】セッションの user_id に該当するユーザーがDBに存在しない場合 404 になるか"""
    with client.session_transaction() as session:
        session['user_id'] = 999999  # 存在しないID

    response = client.get('/mypage')
    assert response.status_code == 404