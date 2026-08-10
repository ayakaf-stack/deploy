# 美しい日本語WEBアプリ

## 概要

美しい日本語の単語や意味を閲覧し、
その単語から着想を得て文章を投稿できるWebアプリケーションです。

美しい日本語に触れることで、
新たな発想や表現力を養うことを目的としています。

---

## 制作背景

日常生活ではあまり目にしない美しい日本語を知る機会が少ないと感じました。

そこで、美しい日本語を知るだけでなく、
その単語を使って文章を書くことで、
日本語への興味や表現力を深められるアプリを制作しました。

---

## 主な機能

- ユーザー登録
- ログイン・ログアウト
- 単語・意味の閲覧
- ランダム表示
- ジャンル検索
- 単語検索
- 意味検索
- 文章投稿
- 文章編集
- 文章削除
- 文章閲覧
- 単語へのいいね
- 文章へのいいね
- マイページ

---

## 使用技術

|項目|技術|
|---|---|
|言語|Python 3.14|
|フレームワーク|Flask|
|DB|MySQL|
|ORM|SQLAlchemy|
|テンプレート|Jinja2|
|CSS|Bootstrap|

---

## システム構成

Browser→Flask→SQLAlchemy→MySQL

---

## データベース

users

words

genres

word_genres

texts

good_words

good_texts

---

## TEST
### 単体テスト環境

ディレクトリ構成
- testsディレクトリ配下に単体テストプログラムを追加
```
.
├── app.py
├── models
│   ├── extensions.py
│   └── models.py
├── README.md
├── requiremenst.txt
├── static
│   ├── css
│   └── js
├── templates
└── tests
    └── test_app.py
```
### 実行コード
簡易表示
```
python -m pytest -q <テストファイル名>
```
詳細表示
```
python -m pytest -vv <テストファイル名>
```

> <テストファイル名>を省略すると全テストを実行

### ブラウザテスト(Selenium)
インストール
```
pip install selenium
```
[selenium](https://www.selenium.dev/ja/)





