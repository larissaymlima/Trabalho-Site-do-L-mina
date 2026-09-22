// Bibliotech - autenticação simples (armazenamento local no navegador)
// Observação: isto é uma demonstração front-end. Não substitui um backend real
// com hashing de senha e banco de dados seguro.
(function () {
    const DEFAULT_AVATAR = "https://api.dicebear.com/9.x/notionists/svg?seed=Aurora";
//(function () { ... })() é uma "caixa fechada" que evita que suas variáveis conflitem com outros scripts. USERS_KEY e SESSION_KEY são os "nomes das gavetas" onde vamos guardar os dados no navegador (localStorage). DEFAULT_AVATAR é a foto usada se ninguém escolher nenhuma.

    let currentUser = null;

    function avatarDoUsuario(usuario) {
        const foto = localStorage.getItem(`lumina_avatar_${usuario?.email || "visitante"}`) || usuario?.foto_perfil;
        return foto && foto !== "default_profile.png" ? foto : DEFAULT_AVATAR;
    }

    async function apiRequest(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", ...(options.headers || {}) },
            ...options
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.mensagem || "Não foi possível concluir a operação.");
        return data;
    }
//são as "ferramentas" básicas..
//getSessionEmail() / setSessionEmail() / clearSession(): controlam quem está logado no momento (é o "crachá" de quem entrou).
//getCurrentUser(): descobre qual usuário está logado agora e traz os dados dele (nome, foto, etc).
//getUsers() / saveUsers(): leem e gravam a lista de contas cadastradas.
//getSessionEmail() / setSessionEmail() / clearSession(): controlam quem está logado no momento (é o "crachá" de quem entrou).
//getCurrentUser(): descobre qual usuário está logado agora e traz os dados dele (nome, foto, etc).

    //elementos
    const authModal = document.getElementById("authModal");
    const closeAuthModal = document.getElementById("closeAuthModal");
    const authArea = document.getElementById("authArea");
    const minhasReservasHomeLink = document.getElementById("minhasReservasHomeLink") || document.getElementById("minhasReservasLink");
    const catalogosEmAlta = document.getElementById("catalogosEmAlta");

    if (!authModal || !closeAuthModal || !authArea) return;

    const tabBtns = document.querySelectorAll(".tab-btn");
    const loginForm = document.getElementById("loginForm");
    const cadastroForm = document.getElementById("cadastroForm");
    const loginMsg = document.getElementById("loginMsg");
    const cadMsg = document.getElementById("cadMsg");
    const authChoice = document.getElementById("authChoice");
    const modalTabs = document.querySelector(".modal-tabs");
    const chooseLoginBtn = document.getElementById("chooseLoginBtn");
    const chooseSignupBtn = document.getElementById("chooseSignupBtn");

    const avatarPicker = document.getElementById("avatarPicker");
    const avatarUpload = document.getElementById("avatarUpload");
    const cadFoto = document.getElementById("cadFoto");

    let pendingReservaBtn = null; // botão "Reservar" que abriu o modal, se houver
//pega, pelo id de cada elemento (os mesmos IDs que colocamos no HTML), uma "referência" para poder controlar cada peça da tela pelo JavaScript — o modal, os botões, os campos do formulário, etc. pendingReservaBtn guarda qual livro a pessoa tentou reservar, caso ela precise logar primeiro.

    //modal open/close
    function openModal(tab) {
        authModal.classList.add("open");
        if (tab) switchTab(tab);
        setMsg(loginMsg, "");
        setMsg(cadMsg, "");
    }

    function closeModal() {
        authModal.classList.remove("open");
        pendingReservaBtn = null;
    }

    function switchTab(tab) {
        if (authChoice) authChoice.hidden = true;
        if (modalTabs) modalTabs.hidden = false;
        tabBtns.forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
        loginForm.hidden = tab !== "login";
        cadastroForm.hidden = tab !== "cadastro";
    }

    function openAuthChoice(reserva) {
        pendingReservaBtn = { dataset: { idLivro: reserva.idLivro, livro: reserva.titulo } };
        authModal.classList.add("open");
        authChoice.hidden = false;
        if (modalTabs) modalTabs.hidden = true;
        loginForm.hidden = true;
        cadastroForm.hidden = true;
        tabBtns.forEach((button) => button.classList.remove("active"));
        setMsg(loginMsg, "");
        setMsg(cadMsg, "");
    }

    chooseLoginBtn?.addEventListener("click", () => switchTab("login"));
    chooseSignupBtn?.addEventListener("click", () => switchTab("cadastro"));
    document.addEventListener("solicitar-login-reserva", (event) => openAuthChoice(event.detail));

    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    closeAuthModal.addEventListener("click", closeModal);
    authModal.addEventListener("click", (e) => {
        if (e.target === authModal) closeModal();
    });

    function setMsg(el, text, isError) {
        el.textContent = text || "";
        el.classList.remove("error", "success");
        if (text) el.classList.add(isError ? "error" : "success");
    }

    async function carregarCatalogosEmAlta() {
        if (!catalogosEmAlta) return;
        const imagens = {
            Fantasia: "ficção cientifíca.jpg",
            Romance: "romance.jpg",
            Terror: "suspense e thriller.jpg",
            Ação: "Classicos.jpg",
            Suspense: "suspense e thriller.jpg",
            Aventura: "desenvolvimento pessoal.jpg"
        };
        try {
            const resposta = await fetch("/catalogos-em-alta");
            const dados = await resposta.json();
            if (!resposta.ok) throw new Error(dados.mensagem || "Não foi possível carregar os catálogos.");
            catalogosEmAlta.innerHTML = dados.catalogos.map((catalogo) => `
                <article class="box">
                    <div class="box-img"><img src="/static/img/${imagens[catalogo.nome_categoria] || "livros.jpg"}" alt="${catalogo.nome_categoria}"></div>
                    <div class="box-content">
                        <h3>${catalogo.nome_categoria}</h3>
                        <a href="/catalogo?id_categoria=${encodeURIComponent(catalogo.id_categoria)}" class="btn">Ver catálogo</a>
                    </div>
                </article>`).join("");
        } catch (error) {
            catalogosEmAlta.innerHTML = `<p class="catalogos-loading">${error.message}</p>`;
        }
    }
//openModal() / closeModal(): mostram ou escondem a janela de login.
//switchTab(): alterna entre a aba "Entrar" e "Criar conta".
//Os addEventListener fazem: clicar no botão "Entrar" abre o modal; clicar no X fecha; clicar fora da caixa (no fundo escuro) também fecha.
//setMsg(): mostra mensagens de erro (vermelho) ou sucesso (verde) embaixo dos formulários.

    // seleção de avatar
    let selectedAvatar = DEFAULT_AVATAR;

    if (avatarPicker) {
        avatarPicker.querySelectorAll(".avatar-option[data-avatar]").forEach((img) => {
            img.addEventListener("click", () => {
                selectedAvatar = img.dataset.avatar;
                if (cadFoto) cadFoto.value = selectedAvatar;
                avatarPicker.querySelectorAll(".avatar-option").forEach((el) => el.classList.remove("selected"));
                img.classList.add("selected");
            });
        });

        const firstAvatar = avatarPicker.querySelector(".avatar-option[data-avatar]");
        if (firstAvatar) firstAvatar.classList.add("selected");
        if (cadFoto) cadFoto.value = selectedAvatar;
    }

    if (avatarUpload) avatarUpload.addEventListener("change", () => {
        const file = avatarUpload.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            selectedAvatar = reader.result; // base64
            if (cadFoto) cadFoto.value = selectedAvatar;
            avatarPicker.querySelectorAll(".avatar-option").forEach((el) => el.classList.remove("selected"));
            // mostra a foto enviada como miniatura selecionada, no lugar do botão "+"
            const uploadLabel = document.getElementById("avatarUploadLabel");
            uploadLabel.style.backgroundImage = `url(${selectedAvatar})`;
            uploadLabel.style.backgroundSize = "cover";
            uploadLabel.style.backgroundPosition = "center";
            uploadLabel.querySelector("span").style.display = "none";
            uploadLabel.classList.add("selected");
        };
        reader.readAsDataURL(file);
    });
//controla os 4 avatares prontos + a opção de enviar foto própria.
//Clicar em um avatar pronto: marca ele como escolhido (borda laranja).
//Clicar no "+" e escolher um arquivo do computador: o FileReader lê a imagem e a transforma em texto (base64) para guardar junto com os dados do usuário, e mostra essa foto no lugar do "+".

    // cadastro
    cadastroForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const usuario = document.getElementById("cadUsuario").value.trim();
        const email = document.getElementById("cadEmail").value.trim().toLowerCase();
        const telefone = document.getElementById("cadTelefone").value.trim();
        const senha = document.getElementById("cadSenha").value;
        const consentimentoLgpd = document.getElementById("cadConsentimento").checked;

        if (!usuario || !email || !telefone || senha.length < 6 || !consentimentoLgpd) {
            setMsg(cadMsg, "Preencha os campos e aceite o consentimento LGPD.", true);
            return;
        }

        try {
            const data = await apiRequest("/leitores", {
                method: "POST",
                body: JSON.stringify({ nome: usuario, email, telefone, senha, foto_perfil: selectedAvatar, consentimento_lgpd: true })
            });
            setMsg(cadMsg, data.mensagem);
            await fazerLogin(email, senha);
            afterLoginSuccess();
            closeModal();
        } catch (error) {
            setMsg(cadMsg, error.message, true);
        }
    });
//quando a pessoa clica em "Criar conta":
//Pega os valores digitados (usuário, email, senha) e a foto escolhida.
//Confere se preencheu tudo certo e se a senha tem 6+ caracteres.
//Confere se aquele email já não está cadastrado.
//Se estiver tudo certo, salva a conta nova, faz login automático e fecha o modal.

    // login
    async function fazerLogin(email, senha) {
        const data = await apiRequest("/login", {
            method: "POST",
            body: JSON.stringify({ email, senha })
        });
        currentUser = data.usuario;
        currentUser.foto_perfil = avatarDoUsuario(currentUser);
        localStorage.setItem(`lumina_avatar_${email}`, currentUser.foto_perfil);
        updateAuthUI();
        return data;
    }

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("loginEmail").value.trim().toLowerCase();
        const senha = document.getElementById("loginSenha").value;

        try {
            await fazerLogin(email, senha);
            setMsg(loginMsg, "Login realizado!");
            afterLoginSuccess();
            closeModal();
        } catch (error) {
            setMsg(loginMsg, error.message, true);
        }
    });

    function afterLoginSuccess() {
        if (currentUser?.tipo_perfil === "FUNCIONARIO") {
            window.location.href = "/gestor";
            return;
        }

        if (pendingReservaBtn) {
            if (!pendingReservaBtn.dataset.idLivro) {
                window.location.href = "/catalogo";
                return;
            }
            reservarLivro(pendingReservaBtn.dataset.idLivro, pendingReservaBtn.dataset.livro, pendingReservaBtn);
            pendingReservaBtn = null;
        }
    }
//quando a pessoa clica em "Entrar":
//Confere se o email existe e a senha bate.
//Se estiver errado, mostra mensagem de erro.
//Se estiver certo, faz login e fecha o modal.
//afterLoginSuccess(): se a pessoa tentou reservar um livro antes de logar, essa função completa a reserva automaticamente assim que ela loga.

    //área de usuário no cabeçalho
    function updateAuthUI() {
        const user = currentUser;
        const themeToggle = document.getElementById("btn-dark-mode");
        authArea.innerHTML = "";
        if (themeToggle) authArea.appendChild(themeToggle);
        if (minhasReservasHomeLink) {
            minhasReservasHomeLink.hidden = !user;
        }

        if (!user) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-auth";
            btn.id = "openAuthBtn";
            btn.textContent = "Entrar";
            btn.addEventListener("click", () => openModal("login"));
            authArea.appendChild(btn);
            return;
        }

        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "user-chip";
        chip.title = "Clique para sair";

        const img = document.createElement("img");
        img.src = avatarDoUsuario(user);
        img.alt = user.nome;

        const span = document.createElement("span");
        span.textContent = user.nome;

        const logoutX = document.createElement("span");
        logoutX.className = "logout-x";
        logoutX.textContent = "×";

        chip.appendChild(img);
        chip.appendChild(span);
        chip.appendChild(logoutX);

        chip.addEventListener("click", abrirMenuPerfil);

        authArea.appendChild(chip);
        criarMenuPerfil();
    }

    function criarMenuPerfil() {
        let menu = document.getElementById("profileDrawer");
        if (menu) menu.remove();
        menu = document.createElement("aside");
        menu.id = "profileDrawer";
        menu.className = "profile-drawer";
        menu.innerHTML = `
            <div class="profile-drawer__header">
                <strong>Meu perfil</strong>
                <button type="button" class="profile-drawer__close" aria-label="Fechar">&times;</button>
            </div>
            <img class="profile-drawer__avatar" src="${avatarDoUsuario(currentUser)}" alt="Avatar de ${currentUser.nome}">
            <p class="profile-drawer__user"></p>
            <button type="button" class="profile-drawer__action" data-profile-action="edit">Editar perfil</button>
            <button type="button" class="profile-drawer__action profile-drawer__action--exit" data-profile-action="logout">Sair</button>
            <form class="profile-edit-form" hidden>
                <label for="profileName">Nome</label>
                <input id="profileName" type="text" required>
                <label for="profilePhone">Telefone</label>
                <input id="profilePhone" type="tel" required>
                <label for="profileCurrentPassword">Senha atual</label>
                <input id="profileCurrentPassword" type="password">
                <label for="profileNewPassword">Nova senha</label>
                <input id="profileNewPassword" type="password" minlength="6">
                <label>Escolha um bonequinho ou uma foto de perfil</label>
                <div class="avatar-picker" id="profileAvatarPicker">
                    <img class="avatar-option" data-avatar="https://api.dicebear.com/9.x/notionists/svg?seed=Aurora" src="https://api.dicebear.com/9.x/notionists/svg?seed=Aurora" alt="Avatar Aurora">
                    <img class="avatar-option" data-avatar="https://api.dicebear.com/9.x/notionists/svg?seed=Sol" src="https://api.dicebear.com/9.x/notionists/svg?seed=Sol" alt="Avatar Sol">
                    <img class="avatar-option" data-avatar="https://api.dicebear.com/9.x/notionists/svg?seed=Lua" src="https://api.dicebear.com/9.x/notionists/svg?seed=Lua" alt="Avatar Lua">
                    <img class="avatar-option" data-avatar="https://api.dicebear.com/9.x/notionists/svg?seed=Estrela" src="https://api.dicebear.com/9.x/notionists/svg?seed=Estrela" alt="Avatar Estrela">
                    <label class="avatar-option avatar-upload" id="profileAvatarUploadLabel">
                        <span>+</span>
                        <input id="profileAvatar" type="file" accept="image/*" hidden>
                    </label>
                </div>
                <button type="submit" class="profile-drawer__action">Salvar alterações</button>
                <p class="profile-drawer__message"></p>
            </form>`;
        document.body.appendChild(menu);
        menu.dataset.profileAvatar = avatarDoUsuario(currentUser);
        menu.querySelectorAll("#profileAvatarPicker .avatar-option[data-avatar]").forEach((avatar) => {
            avatar.addEventListener("click", () => {
                menu.dataset.profileAvatar = avatar.dataset.avatar;
                menu.querySelectorAll("#profileAvatarPicker .avatar-option").forEach((item) => item.classList.remove("selected"));
                avatar.classList.add("selected");
            });
        });
        const profileAvatarUpload = menu.querySelector("#profileAvatar");
        profileAvatarUpload.addEventListener("change", () => {
            if (!profileAvatarUpload.files[0]) return;
            menu.dataset.profileAvatar = "";
            menu.querySelectorAll("#profileAvatarPicker .avatar-option").forEach((item) => item.classList.remove("selected"));
            menu.querySelector("#profileAvatarUploadLabel").classList.add("selected");
        });
        menu.querySelector(".profile-drawer__user").textContent = currentUser.email;
        menu.querySelector(".profile-drawer__close").addEventListener("click", fecharMenuPerfil);
        menu.querySelector("[data-profile-action='edit']").addEventListener("click", abrirEdicaoPerfil);
        menu.querySelector("[data-profile-action='logout']").addEventListener("click", sair);
        menu.querySelector(".profile-edit-form").addEventListener("submit", salvarPerfil);
        menu.querySelector("#profileName").value = currentUser.nome || "";
        menu.querySelector("#profilePhone").value = currentUser.telefone || "";
        menu.querySelector("[data-profile-action='edit']").hidden = currentUser.tipo_perfil !== "LEITOR";
    }

    function abrirMenuPerfil() {
        const menu = document.getElementById("profileDrawer");
        if (menu) menu.classList.add("profile-drawer--open");
    }

    function fecharMenuPerfil() {
        const menu = document.getElementById("profileDrawer");
        if (menu) menu.classList.remove("profile-drawer--open");
    }

    function abrirEdicaoPerfil() {
        const menu = document.getElementById("profileDrawer");
        menu.querySelector(".profile-edit-form").hidden = false;
        menu.querySelector("[data-profile-action='edit']").hidden = true;
    }

    async function salvarPerfil(event) {
        event.preventDefault();
        const menu = event.currentTarget.parentElement;
        const mensagem = menu.querySelector(".profile-drawer__message");
        const nome = menu.querySelector("#profileName").value.trim();
        const telefone = menu.querySelector("#profilePhone").value.trim();
        const senhaAtual = menu.querySelector("#profileCurrentPassword").value;
        const novaSenha = menu.querySelector("#profileNewPassword").value;
        try {
            if (!nome || !telefone) throw new Error("Nome e telefone são obrigatórios.");
            const arquivo = menu.querySelector("#profileAvatar").files[0];
            const avatarSelecionado = menu.dataset.profileAvatar || avatarDoUsuario(currentUser);
            if (!avatarSelecionado && !arquivo) throw new Error("Escolha um bonequinho ou envie uma foto.");
            await apiRequest("/leitores/dados", { method: "PUT", body: JSON.stringify({ nome, telefone, foto_perfil: avatarSelecionado || avatarDoUsuario(currentUser) }) });
            let fotoAtualizada = avatarSelecionado || avatarDoUsuario(currentUser);
            if (senhaAtual || novaSenha) {
                if (!senhaAtual || !novaSenha) throw new Error("Informe a senha atual e a nova senha.");
                await apiRequest("/leitores/senha", { method: "PUT", body: JSON.stringify({ senha_atual: senhaAtual, nova_senha: novaSenha }) });
            }
            if (arquivo) {
                const dados = new FormData();
                dados.append("foto", arquivo);
                const resposta = await fetch("/leitores/avatar", { method: "POST", credentials: "same-origin", body: dados });
                const resultado = await resposta.json();
                if (!resposta.ok) throw new Error(resultado.mensagem || "Não foi possível atualizar a foto.");
                fotoAtualizada = resultado.foto_perfil;
            }
            currentUser.nome = nome;
            currentUser.telefone = telefone;
            currentUser.foto_perfil = fotoAtualizada;
            localStorage.setItem(`lumina_avatar_${currentUser.email}`, currentUser.foto_perfil);
            mensagem.textContent = "Perfil atualizado com sucesso.";
            updateAuthUI();
            abrirMenuPerfil();
        } catch (error) {
            mensagem.textContent = error.message;
        }
    }

    function sair() {
        apiRequest("/logout", { method: "POST" }).finally(() => {
            currentUser = null;
            const menu = document.getElementById("profileDrawer");
            if (menu) menu.remove();
            updateAuthUI();
        });
    }
//atualiza o que aparece no canto do cabeçalho.
//Se ninguém está logado: mostra o botão "Entrar".
//Se alguém está logado: mostra a foto + nome do usuário, num "chip" clicável. Clicar nele pergunta se a pessoa quer sair (logout).

    // botões "Reservar" exigem login
    document.querySelectorAll(".btn-reservar").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const user = currentUser;
            if (!user) {
                pendingReservaBtn = btn;
                openModal("login");
                return;
            }
            if (!btn.dataset.idLivro) {
                window.location.href = "/catalogo";
                return;
            }
            reservarLivro(btn.dataset.idLivro, btn.dataset.livro, btn);
        });
    });
//: pega todos os botões com a classe btn-reservar (os 6 que marcamos no HTML). Ao clicar:
//Se não estiver logado: abre o modal de login e guarda qual livro era, para reservar automaticamente depois do login.
//Se já estiver logado: confirma a reserva na hora.

    async function carregarSessao() {
        try {
            const data = await apiRequest("/me", { headers: {} });
            currentUser = data.usuario;
            currentUser.foto_perfil = avatarDoUsuario(currentUser);
        } catch (error) {
            currentUser = null;
        }
        updateAuthUI();
    }

    async function reservarLivro(idLivro, titulo, btn) {
        try {
            const data = await apiRequest("/reservas", {
                method: "POST",
                body: JSON.stringify({ id_livro: idLivro })
            });
            alert(data.mensagem || `Reserva realizada para: ${titulo}`);
            btn.disabled = true;
        } catch (error) {
            alert(error.message);
        }
    }

    carregarSessao();
    carregarCatalogosEmAlta();
})();
//roda a função updateAuthUI() assim que a página carrega, para já mostrar corretamente se tem alguém logado ou não. O })(); fecha a "caixa" que abrimos lá na Parte 1.