document.addEventListener("DOMContentLoaded", () => {
    let currentType = "word";
    let selectedGenres = [];

    const searchInput = document.getElementById("search_input");
    const sortSelect = document.getElementById("sort_select");
    const genreList = document.getElementById("genre_list");
    const listContainer = document.getElementById("list_container");
    const noResult = document.getElementById("no_result");

    // タブ切り替え
    const toggleBtns = document.querySelectorAll(".toggle_btn");
    toggleBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            currentType = btn.dataset.type;

            toggleBtns.forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");

            genreList.style.display = currentType === "word" ? "flex" : "none";
            
            updateSortOptions();
            fetchAndRender();
        });
    });

    function updateSortOptions() {
        if (currentType === "word") {
            sortSelect.innerHTML = `
                <option value="">並び替え</option>
                <option value="aiueo_asc">あいうえお順(昇順)</option>
                <option value="aiueo_desc">あいうえお順(降順)</option>
                <option value="good_desc">いいねが多い順</option>
            `;
        } else {
            sortSelect.innerHTML = `
                <option value="">並び替え</option>
                <option value="date_desc">登録日が新しい順</option>
                <option value="date_asc">登録日が古い順</option>
                <option value="good_desc">いいねが多い順</option>
            `;
        }
    }

    // キーワード検索(即時反映)
    searchInput.addEventListener("input", () => {
        fetchAndRender();
    });

    // ソート変更
    sortSelect.addEventListener("change", () => {
        fetchAndRender();
    });

    // ジャンル選択(複数可)
    genreList.addEventListener("click", (e) => {
        if (!e.target.classList.contains("genre_btn")) return;

        const genreId = e.target.dataset.genreId;
        e.target.classList.toggle("selected");

        if (selectedGenres.includes(genreId)) {
            selectedGenres = selectedGenres.filter(id => id !== genreId);
        } else {
            selectedGenres.push(genreId);
        }
        fetchAndRender();
    });

    async function fetchAndRender() {
        const params = new URLSearchParams();
        params.set("type", currentType);
        params.set("q", searchInput.value.trim());
        params.set("sort", sortSelect.value);
        selectedGenres.forEach(id => params.append("genre", id));

        const response = await fetch(`/contents?${params.toString()}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        const data = await response.json();

        renderList(data.type, data.items);
    }

    function renderList(type, items) {
        listContainer.innerHTML = "";

        if (items.length === 0) {
            noResult.style.display = "block";
            return;
        }
        noResult.style.display = "none";

        items.forEach(item => {
            const li = document.createElement("li");

            if (type === "word") {
                li.className = "word_item";
                li.innerHTML = `
                    <p><span class="item_word">${item.word}</span></p>
                    <p><span class="item_reading">【${item.reading}】</span></p>
                    <p><span class="item_mean">${item.mean}</span></p>
                    <form class="good-form" action="/good/word/${item.id}" method="POST">
                        <button type="submit" class="good-button${item.is_good ? " is-liked" : ""}" aria-label="お気に入り">
                            <svg class="bookmark-icon" width="18" height="22" viewBox="0 0 24 30">
                                <path d="M5 3 H19 V27 L12 20.5 L5 27 Z"/>
                            </svg>
                        </button>
                        <span class="good-count">${item.good_count}</span>
                    </form>
                    <a href="/text-new/${item.id}">文章作成</a>
                `;
            } else {
                li.className = "text_item";
                li.innerHTML = `
                    <span class="text_label">タイトル</span>
                    <p class="text_title_display">${item.title}</p>

                    <details class="text_drawer">
                        <summary class="drawer_btn">本文を表示</summary>
                        <p class="drawer_content white-space">${item.main_text}</p>
                    </details>

                    <form class="good-form" action="/good/text/${item.id}" method="POST">
                        <button type="submit" class="good-button${item.is_good ? " is-liked" : ""}" aria-label="お気に入り">
                            <svg class="bookmark-icon" width="18" height="22" viewBox="0 0 24 30">
                                <path d="M5 3 H19 V27 L12 20.5 L5 27 Z"/>
                            </svg>
                        </button>
                        <span class="good-count">${item.good_count}</span>
                    </form>
                `;
            }

            listContainer.appendChild(li);
        });
    }
});