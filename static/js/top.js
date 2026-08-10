document.addEventListener("DOMContentLoaded", () => {
    const nextBtn = document.getElementById("next_word_btn");
    const INITIAL_BACKGROUND_COLOR = "#062c54";

    // 暗めのランダム背景色を生成する関数（金色の視認性を高めるため背景を暗めに固定）
    function generateRandomDarkColor() {
        const h = Math.floor(Math.random() * 360);
        const s = Math.floor(Math.random() * 16) + 20; 
        const l = Math.floor(Math.random() * 10) + 15;
        return `hsl(${h}, ${s}%, ${l}%)`;
    }

    function applyBackgroundColor(color) {
        setTimeout(() => {
            document.body.style.backgroundColor = color;
        }, 100); 
    }

    // ★ 未ログイン時の文章作成クリック制御
    function setupTextNewLinkHandler() {
        const textNewLink = document.getElementById("text_new_link");
        if (textNewLink) {
            textNewLink.addEventListener("click", (e) => {
                const isLogin = textNewLink.getAttribute("data-login") === "true";
                if (!isLogin) {
                    e.preventDefault(); // 画面遷移をブロック
                    // good.js で定義されている共通のフラッシュメッセージ関数を呼び出す
                    showFlashMessage('文章作成機能を使うには<a href="/login">ログイン</a>してください');
                }
            });
        }
    }

    // 初回読み込み時の設定
    setupTextNewLinkHandler();

    nextBtn.addEventListener("click", async () => {
        // ...（次へボタンのAjax処理）...
        
        // ★ Ajaxで単語が切り替わった後、新しく生成されたリンクのログイン状態も更新
        const textNewLink = document.getElementById("text_new_link");
        textNewLink.href = `/text-new/${data.word.id}`;
        if (data.is_login !== undefined) {
            textNewLink.setAttribute("data-login", data.is_login ? "true" : "false");
        }

        // ...（文章一覧の書き換え処理など）...

        // ★ 再構築されたリンクにイベントを再バインド
        setupTextNewLinkHandler();
    });


    // 初回読み込み時の設定
    setupTextNewLinkHandler();


    nextBtn.addEventListener("click", async () => {
        const nextColor = generateRandomDarkColor();
        applyBackgroundColor(nextColor);
        const response = await fetch("/", {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        const data = await response.json();

        // 単語部分を書き換え
        document.getElementById("word_text").textContent = data.word.word;
        document.getElementById("word_reading").textContent = `【 ${data.word.reading} 】`;
        document.getElementById("word_mean").textContent = data.word.mean;

        const wordForm = document.getElementById("word_good_form");
        wordForm.action = `/good/word/${data.word.id}`;

        const wordButton = wordForm.querySelector(".good-button");
        wordButton.classList.toggle("is-liked", data.is_good);

        wordForm.querySelector(".good-count").textContent = data.good_count;

        // ★ Ajaxで切り替わった後も data-login 属性を維持して href を更新
        // ※バックエンドの jsonify に is_login を含める必要があります（後述）
        const textNewLink = document.getElementById("text_new_link");
        textNewLink.href = `/text-new/${data.word.id}`;
        // data.is_login が渡ってくる前提で属性を再設定
        if (data.is_login !== undefined) {
            textNewLink.setAttribute("data-login", data.is_login ? "true" : "false");
        }

        // 文章一覧を書き換え(見出し + スクロール枠を復元)
        const textListArea = document.getElementById("text_list_area");
        textListArea.innerHTML = `
            <p class="section-title">この単語から作成された文章</p>
            <div class="text_scroll_list"></div>
        `;
        const scrollList = textListArea.querySelector(".text_scroll_list");

        data.texts.forEach(text => {
            const div = document.createElement("div");
            div.className = "text_item";
            div.innerHTML = `
                <span class="text_label">タイトル</span>
                <p class="text_title_display">${text.title}</p>

                <details class="text_drawer">
                    <summary class="drawer_btn">本文を表示</summary>
                    <p class="drawer_content white-space">${text.main_text}</p>
                </details>

                <form class="good-form" action="/good/text/${text.id}" method="POST">
                    <button type="submit" class="good-button${text.is_good ? " is-liked" : ""}" aria-label="お気に入り">
                        <svg class="bookmark-icon" width="18" height="22" viewBox="0 0 24 30">
                            <path d="M5 3 H19 V27 L12 20.5 L5 27 Z"/>
                        </svg>
                    </button>
                    <span class="good-count">${text.good_count}</span>
                </form>
            `;
            scrollList.appendChild(div);
        });
        
        // ★ AjaxでHTMLが再構築されるため、再バインドを実行
        setupTextNewLinkHandler();
    });
});