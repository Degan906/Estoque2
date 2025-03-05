import streamlit as st
import pandas as pd
import requests
import base64
import io
import json
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Controle de Estoque e Orçamentos", layout="wide")

# Substitua pelo seu token do GitHub
GITHUB_REPO = "https://api.github.com/repos/Degan906/Estoque2/contents"
GITHUB_TOKEN = "seu_novo_token_aqui"  # Substitua pelo seu token
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def ler_csv_do_github(nome_arquivo):
    url = f"{GITHUB_REPO}/{nome_arquivo}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        conteudo = base64.b64decode(response.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(conteudo))
    else:
        st.error(f"Erro ao ler {nome_arquivo} do GitHub: {response.text}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

def gravar_csv_no_github(nome_arquivo, df):
    url = f"{GITHUB_REPO}/{nome_arquivo}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        conteudo_atual = response.json()
        sha = conteudo_atual["sha"]  # Obter o SHA do arquivo atual
    else:
        st.error(f"Erro ao ler {nome_arquivo} do GitHub: {response.text}")
        return

    conteudo = df.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo.encode("utf-8")).decode("utf-8")
    data = {
        "message": f"Atualizando {nome_arquivo}",
        "content": conteudo_base64,
        "sha": sha  # Incluir o SHA para atualizar o arquivo
    }

    response = requests.put(url, headers=HEADERS, json=data)
    if response.status_code not in [200, 201]:
        st.error(f"Erro ao gravar {nome_arquivo} no GitHub: {response.text}")
    else:
        st.success(f"{nome_arquivo} atualizado com sucesso!")

def carregar_dados():
    produtos = ler_csv_do_github("produtos.csv")
    usuarios = ler_csv_do_github("usuarios.csv")
    estoque = ler_csv_do_github("estoque.csv")
    vendas = ler_csv_do_github("vendas.csv")
    orcamentos = ler_csv_do_github("orcamentos.csv")

    # Inicializar DataFrames vazios se necessário
    if orcamentos.empty:
        orcamentos = pd.DataFrame(columns=["orcamento_id", "data", "total", "produtos", "status"])
    if estoque.empty:
        estoque = pd.DataFrame(columns=["produto_id", "nome", "quantidade"])
    if usuarios.empty:
        usuarios = pd.DataFrame(columns=["id", "nome", "email", "senha"])  # Adicione a coluna "senha"

    # Converter colunas de data
    if "data" in orcamentos.columns:
        orcamentos["data"] = pd.to_datetime(orcamentos["data"], format="%d/%m/%y %H:%M", errors="coerce")
    if "data" in vendas.columns:
        vendas["data"] = pd.to_datetime(vendas["data"], format="%d/%m/%y %H:%M", errors="coerce")

    # Converter colunas numéricas
    if "produto_id" in estoque.columns:
        estoque["produto_id"] = pd.to_numeric(estoque["produto_id"], errors="coerce").fillna(0).astype(int)
    if "preco" in produtos.columns:
        produtos["preco"] = pd.to_numeric(produtos["preco"], errors="coerce")
    if "id" in produtos.columns:
        produtos["id"] = pd.to_numeric(produtos["id"], errors="coerce").fillna(0).astype(int)

    return produtos, usuarios, estoque, orcamentos, vendas

# Carregar dados
produtos, usuarios, estoque, orcamentos, vendas = carregar_dados()

# Inicializar os dados na sessão
if "usuarios" not in st.session_state:
    st.session_state.usuarios = usuarios

# Verificar se a coluna 'senha' existe
if isinstance(st.session_state.usuarios, pd.DataFrame):
    if "senha" in st.session_state.usuarios.columns:
        st.session_state.usuarios["senha"] = st.session_state.usuarios["senha"].astype(str)
    else:
        st.warning("A coluna 'senha' não existe no DataFrame de usuários.")
else:
    st.error("Erro: `usuarios` não é um DataFrame.")

# Inicializar os dados na sessão
if "produtos" not in st.session_state:
    st.session_state.produtos, st.session_state.usuarios, st.session_state.estoque, st.session_state.orcamentos, st.session_state.vendas = carregar_dados()

# Função para salvar dados de volta nos arquivos CSV no GitHub
def salvar_dados(produtos=None, estoque=None, orcamentos=None, vendas=None):
    if produtos is not None:
        gravar_csv_no_github("produtos.csv", produtos)
    if estoque is not None:
        gravar_csv_no_github("estoque.csv", estoque)
    if orcamentos is not None:
        gravar_csv_no_github("orcamentos.csv", orcamentos)
    if vendas is not None:
        gravar_csv_no_github("vendas.csv", vendas)

# Função auxiliar para converter tipos Pandas para tipos nativos do Python
def converter_para_json_serializavel(obj):
    if isinstance(obj, pd.Series):
        obj = obj.to_dict()  # Converte Series para dicionário
    if isinstance(obj, dict):
        return {k: converter_para_json_serializavel(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [converter_para_json_serializavel(v) for v in obj]
    elif isinstance(obj, (np.int64, np.int32)):  # Tratar tipos inteiros do NumPy
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):  # Tratar tipos de ponto flutuante do NumPy
        return float(obj)
    else:
        return obj

# Verificar se o usuário está logado
if "logado" not in st.session_state:
    st.session_state.logado = False

# Tela de Login
if not st.session_state.logado:
    st.title("Login")
    email = st.text_input("Email").strip().lower()
    senha = st.text_input("Senha", type="password").strip()
    if st.button("Entrar"):
        # Verificação de dados de login para admin
        if email == "admin" and senha == "admin":
            st.session_state.logado = True
            st.success("Login administrativo realizado com sucesso!")
        else:
            # Verificação de dados de login para usuários comuns
            st.session_state.usuarios["senha"] = st.session_state.usuarios["senha"].astype(str)
            usuario = st.session_state.usuarios[
                (st.session_state.usuarios["email"].str.strip().str.lower() == email) & 
                (st.session_state.usuarios["senha"].str.strip() == senha)
            ]
            if not usuario.empty:
                st.session_state.logado = True
                st.success("Login realizado com sucesso!")
            else:
                st.error("Email ou senha inválidos.")

# Sistema Principal (após login)
else:
    # Botão de atualização no menu lateral
    if st.sidebar.button("Atualizar Dados"):
        st.session_state.produtos, st.session_state.usuarios, st.session_state.estoque, st.session_state.orcamentos, st.session_state.vendas = carregar_dados()
        st.success("Dados atualizados com sucesso!")

    # Menu lateral
    menu = st.sidebar.selectbox(
        "Menu",
        [
            "Dashboard", 
            "Cadastro de Produtos",
            "Entrada no Estoque",
            "Criar Orçamento",
            "Validar Orçamento",
            "Relatório de Vendas",
            "Zerar Estoque",
            "Cadastrar Usuário",
            "Logout"
        ]
    )

    if menu == "Dashboard":
        st.title("Dashboard")
        st.write("Bem-vindo ao sistema de controle de estoque e orçamentos!") 

        # Exibir a tabela de estoque completa
        st.subheader("Tabela de Estoque Completa")
        if st.session_state.estoque is not None:
            try:
                if "produto_id" not in st.session_state.estoque.columns or "nome" not in st.session_state.estoque.columns or "quantidade" not in st.session_state.estoque.columns:
                    st.error("Alguma coluna necessária não foi encontrada no arquivo 'estoque.csv'.")
                else:
                    st.dataframe(st.session_state.estoque[["produto_id", "nome", "quantidade"]])
                    
                    st.subheader("Resumo do Estoque")
                    total_produtos = len(st.session_state.estoque)
                    total_quantidade = st.session_state.estoque["quantidade"].sum()
                    st.metric("Total de Produtos no Estoque", total_produtos)
                    st.metric("Quantidade Total em Estoque", total_quantidade)
            except Exception as e:
                st.error(f"Erro ao processar a tabela de estoque: {str(e)}")
        else:
            st.error("Erro ao carregar o estoque. Verifique o arquivo 'estoque.csv' no repositório do GitHub.")

    elif menu == "Cadastro de Produtos":
        st.title("Cadastro de Produtos")

        # Lista de produtos cadastrados
        produtos_list = st.session_state.produtos["nome"].tolist() if not st.session_state.produtos.empty else []
        produto_selecionado = st.selectbox("Selecione o Produto para Editar", ["---"] + produtos_list)

        if produto_selecionado != "---":
            # Obter os dados do produto selecionado
            produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
            produto_nome_atual = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "nome"].values[0]
            produto_preco_atual = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "preco"].values[0]

            # Formulário para editar o produto
            with st.form("editar_produto"):
                st.subheader(f"Editar Produto: {produto_nome_atual}")
                novo_nome = st.text_input("Novo Nome do Produto", value=produto_nome_atual)
                novo_preco = st.number_input("Novo Preço", min_value=0.0, value=float(produto_preco_atual), format="%.2f")
                submitted = st.form_submit_button("Salvar Alterações")
                if submitted:
                    # Atualizar o produto no DataFrame
                    st.session_state.produtos.loc[st.session_state.produtos["id"] == produto_id, "nome"] = novo_nome
                    st.session_state.produtos.loc[st.session_state.produtos["id"] == produto_id, "preco"] = novo_preco
                    
                    # Salvar os dados no GitHub
                    salvar_dados(produtos=st.session_state.produtos)
                    st.success(f"Produto '{produto_nome_atual}' editado com sucesso!")

        # Formulário para cadastrar novos produtos
        with st.form("cadastro_produto"):
            st.subheader("Cadastrar Novo Produto")
            nome = st.text_input("Nome do Produto")
            preco = st.number_input("Preço", min_value=0.0, format="%.2f")
            submitted = st.form_submit_button("Cadastrar")
            
            if submitted:
                # Garantir que a coluna 'id' seja do tipo inteiro
                st.session_state.produtos["id"] = pd.to_numeric(st.session_state.produtos["id"], errors="coerce").fillna(0).astype(int)
                
                # Calcular o próximo ID
                novo_id = st.session_state.produtos["id"].max() + 1 if not st.session_state.produtos.empty else 1
                
                # Criar o novo produto
                novo_produto = pd.DataFrame({"id": [novo_id], "nome": [nome], "preco": [preco], "quantidade": [0]})
                st.session_state.produtos = pd.concat([st.session_state.produtos, novo_produto], ignore_index=True)

                # Adicionar o produto ao estoque com quantidade 0
                novo_estoque = pd.DataFrame({
                    "produto_id": [novo_id],
                    "nome": [nome],
                    "quantidade": [0]
                })
                st.session_state.estoque = pd.concat([st.session_state.estoque, novo_estoque], ignore_index=True)

                # Salvar os dados no GitHub
                salvar_dados(produtos=st.session_state.produtos, estoque=st.session_state.estoque)
                st.success(f"Produto '{nome}' cadastrado com sucesso e adicionado ao estoque!")

        # Exibir a lista de produtos cadastrados
        st.subheader("Produtos Cadastrados")
        if st.session_state.produtos is not None and not st.session_state.produtos.empty:
            st.dataframe(st.session_state.produtos[["id", "nome", "preco"]])
        else:
            st.warning("Nenhum produto cadastrado.")

    elif menu == "Entrada no Estoque":
        st.title("Entrada no Estoque")
        produtos_list = st.session_state.produtos["nome"].tolist()
        produto_selecionado = st.selectbox("Selecione o Produto", produtos_list)
        
        produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
        produto_nome = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "nome"].values[0]
        
        # Verifique se o produto existe no estoque
        estoque_produto = st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id]

        if not estoque_produto.empty:
            estoque_disponivel = estoque_produto["quantidade"].values[0]
        else:
            # Se o produto não estiver no estoque, adicione-o com quantidade 0
            novo_estoque = pd.DataFrame({
                "produto_id": [produto_id],
                "nome": [produto_nome],
                "quantidade": [0]
            })
           
            st.session_state.estoque = pd.concat([st.session_state.estoque, novo_estoque], ignore_index=True)
            estoque_disponivel = 0
            st.warning(f"Produto '{produto_selecionado}' adicionado ao estoque com quantidade 0.")

        # Exibir a quantidade em estoque
        st.write(f"Quantidade em estoque: **{estoque_disponivel}** unidades")

        # Campo para informar a quantidade desejada
        quantidade = st.number_input("Quantidade", min_value=1)

        if st.button("Registrar Entrada"):
            if not estoque_produto.empty:
                st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id, "quantidade"] += quantidade
            else:
                st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id, "quantidade"] = quantidade
            
            salvar_dados(estoque=st.session_state.estoque)
            st.success(f"{quantidade} unidades de '{produto_selecionado}' adicionadas ao estoque.")

    elif menu == "Criar Orçamento":
        st.title("Criar Orçamento")
        
        # Verificar se st.session_state.orcamento_atual é None e reinicializá-lo
        if "orcamento_atual" not in st.session_state or st.session_state.orcamento_atual is None:
            # Gerar um novo ID para o orçamento
            novo_id = st.session_state.orcamentos["orcamento_id"].max() + 1 if not st.session_state.orcamentos.empty else 1
            st.session_state.orcamento_atual = {
                "orcamento_id": novo_id,
                "data": datetime.now().strftime("%d/%m/%y %H:%M"),
                "itens": [],  # Lista de itens do orçamento
                "total": 0.0  # Total do orçamento
            }
         
        # Exibir o ID do orçamento e a data
        st.subheader(f"Orçamento ID: {st.session_state.orcamento_atual['orcamento_id']}")
        st.write(f"Data: {st.session_state.orcamento_atual['data']}")
        
        # SubGrupo: Tabela para adicionar produtos
        st.subheader("Adicionar Produtos ao Orçamento")
        
        # Lista de produtos disponíveis
        produtos_list = st.session_state.produtos["nome"].tolist()
        produto_selecionado = st.selectbox("Selecione o Produto", produtos_list)
        
        # Obter o ID e o preço do produto selecionado
        produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
        preco_unitario = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "preco"].values[0]
        
        # Verificar se o produto existe no estoque (apenas para exibição)
        estoque_produto = st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id]
        quantidade_estoque = estoque_produto["quantidade"].values[0] if not estoque_produto.empty else 0
        
        # Exibir a quantidade em estoque (se existir)
        st.write(f"Quantidade em estoque: **{quantidade_estoque}** unidades")
        
        # Campo para informar a quantidade desejada
        quantidade = st.number_input("Quantidade", min_value=1)
        
        # Campo para o preço (editável)
        preco_orcamento = st.number_input("Preço Unitário (R$)", value=float(preco_unitario), format="%.2f")

        # Campo para observações
        obs = st.text_input("Observações")
        
        # Botão para adicionar o produto ao orçamento
        if st.button("Adicionar Produto"):
            try:
                # Converter preco_orcamento e quantidade para float
                preco_orcamento = float(preco_orcamento)
                quantidade = float(quantidade)
                
                # Calcular o total do produto
                total_produto = preco_orcamento * quantidade
                
                # Adicionar o item ao orçamento
                item = {
                    "produto_id": produto_id,
                    "nome": produto_selecionado,
                    "quantidade": quantidade,
                    "preco_unitario": preco_orcamento,  # Usar o preço do orçamento
                    "total": float(total_produto),
                    "obs": obs  # Adicionar observações
                }
                st.session_state.orcamento_atual["itens"].append(item)
                
                # Atualizar o total do orçamento
                st.session_state.orcamento_atual["total"] += total_produto
                st.success(f"{quantidade} unidades de '{produto_selecionado}' adicionadas ao orçamento.")
            except ValueError as e:
                st.error(f"Erro ao calcular o total do produto: {e}. Verifique se os valores de preço e quantidade são números válidos.")
        
        # Exibir a tabela de itens do orçamento
        if st.session_state.orcamento_atual["itens"]:
            st.subheader("Itens no Orçamento")
            itens_df = pd.DataFrame(st.session_state.orcamento_atual["itens"])
            st.dataframe(itens_df[["nome", "quantidade", "preco_unitario", "total", "obs"]])
            
            # Adicionar funcionalidade para remover itens
            st.subheader("Remover Produto do Orçamento")
            produto_para_remover = st.selectbox(
                "Selecione o Produto para Remover",
                [item["nome"] for item in st.session_state.orcamento_atual["itens"]]
            )
            if st.button("Remover Produto"):
                # Encontrar o item a ser removido
                item_para_remover = next(
                    (item for item in st.session_state.orcamento_atual["itens"] if item["nome"] == produto_para_remover),
                    None
                )
                if item_para_remover:
                    # Subtrair o total do item do total do orçamento
                    st.session_state.orcamento_atual["total"] -= item_para_remover["total"]
                    # Remover o item da lista
                    st.session_state.orcamento_atual["itens"] = [
                        item for item in st.session_state.orcamento_atual["itens"] if item["nome"] != produto_para_remover
                    ]
                    st.success(f"Produto '{produto_para_remover}' removido do orçamento.")
                else:
                    st.error("Produto não encontrado no orçamento.")
        
        # Rodapé: Valor total do orçamento
        st.subheader(f"Total do Orçamento: R$ {st.session_state.orcamento_atual['total']:.2f}")
        
        # Botões lado a lado usando colunas
        col1, col2, col3, col4 = st.columns(4)  # 4 colunas para os botões

        with col1:
            if st.button("Finalizar Orçamento"):
                if st.session_state.orcamento_atual["itens"]:
                    # Criar um novo orçamento
                    novo_orcamento = {
                        "orcamento_id": st.session_state.orcamento_atual["orcamento_id"],
                        "data": st.session_state.orcamento_atual["data"],
                        "total": float(st.session_state.orcamento_atual["total"]),
                        "produtos": json.dumps(converter_para_json_serializavel(st.session_state.orcamento_atual["itens"])),
                        "status": "Pendente"  # Status inicial do orçamento
                    }
                    st.session_state.orcamentos = pd.concat([st.session_state.orcamentos, pd.DataFrame([novo_orcamento])], ignore_index=True)
                    
                    # Salvar os dados no GitHub
                    salvar_dados(orcamentos=st.session_state.orcamentos)
                    
                    # Limpar a sessão de orçamento
                    st.session_state.orcamento_atual = None
                    st.success("Orçamento finalizado com sucesso!")
                else:
                    st.error("Não há itens no orçamento para finalizar.")

        with col2:
            if st.button("Imprimir Cupom"):
                if st.session_state.orcamento_atual and st.session_state.orcamento_atual["itens"]:
                    # Gerar o cabeçalho do cupom
                    cupom = "Testes de cupom de Venda\n"
                    cupom += "+" * 35 + "\n"
                    cupom += f"Venda id: {st.session_state.orcamento_atual['orcamento_id']:04d}   Data/Hora: {st.session_state.orcamento_atual['data']}\n"
                    cupom += "+" * 35 + "\n"
                    cupom += "Descrição:              QT:      Preço          Total       Obs\n"
                     
                    # Gerar o corpo do cupom
                    for item in st.session_state.orcamento_atual["itens"]:
                        nome = item["nome"]
                        qtde = item["quantidade"]
                        
                        # Converter preco_unitario e total para float
                        try:
                            preco_unitario = float(item["preco_unitario"])
                            total = float(item["total"])
                        except ValueError as e:
                            st.error(f"Erro ao converter valores para float: {e}")
                            continue  # Pula este item se houver erro de conversão
                        
                        # Adicionar o item ao cupom
                        cupom += f"{nome:3}     R${preco_unitario:>6.2f} x R${total:>6.2f}   {item.get('obs', '')}\n"

                    # Gerar o rodapé do cupom
                    cupom += "+" * 35 + "\n"
                    cupom += f"Total da Venda: R${float(st.session_state.orcamento_atual['total']):>6.2f}\n"
                    
                    # Exibir o cupom no Streamlit
                    st.text(cupom)
                else:
                    st.error("Não há itens no orçamento para imprimir o cupom.")

        with col3:
            if st.button("Lançar Venda"):
                if st.session_state.orcamento_atual and st.session_state.orcamento_atual["itens"]:
                    # Criar uma nova venda
                    nova_venda = {
                        "venda_id": len(st.session_state.vendas) + 1,
                        "data": datetime.now().strftime("%d/%m/%y %H:%M"),
                        "total": float(st.session_state.orcamento_atual["total"]),
                        "produtos": json.dumps(converter_para_json_serializavel(st.session_state.orcamento_atual["itens"]))
                    }
                    st.session_state.vendas = pd.concat([st.session_state.vendas, pd.DataFrame([nova_venda])], ignore_index=True)
                    
                    # Atualizar o status do orçamento para "Validado"
                    novo_orcamento = {
                        "orcamento_id": st.session_state.orcamento_atual["orcamento_id"],
                        "data": st.session_state.orcamento_atual["data"],
                        "total": float(st.session_state.orcamento_atual["total"]),
                        "produtos": json.dumps(converter_para_json_serializavel(st.session_state.orcamento_atual["itens"])),
                        "status": "Validado"  # Alterar status para Validado
                    }
                    st.session_state.orcamentos = pd.concat([st.session_state.orcamentos, pd.DataFrame([novo_orcamento])], ignore_index=True)
                    
                    # Salvar os dados no GitHub
                    salvar_dados(vendas=st.session_state.vendas, orcamentos=st.session_state.orcamentos)
                    
                    # Limpar a sessão de orçamento
                    st.session_state.orcamento_atual = None
                    st.success("Venda lançada e orçamento validado com sucesso!")
                else:
                    st.error("Não há itens no orçamento para lançar a venda.")

        with col4:
            if st.button("Enviar por WhatsApp"):
                if st.session_state.orcamento_atual and st.session_state.orcamento_atual["itens"]:
                    # Gerar o texto do cupom
                    cupom = "Testes de cupom de Venda\n"
                    cupom += "+" * 35 + "\n"
                    cupom += f"Venda id: {st.session_state.orcamento_atual['orcamento_id']:04d}   Data/Hora: {st.session_state.orcamento_atual['data']}\n"
                    cupom += "+" * 35 + "\n"
                    cupom += "Descrição:               QT:      Preço           Total       Obs\n"
                    
                    # Gerar o corpo do cupom
                    for item in st.session_state.orcamento_atual["itens"]:
                        nome = item["nome"]
                        qtde = item["quantidade"]
                        
                        # Converter preco_unitario e total para float
                        try:
                            preco_unitario = float(item["preco_unitario"])
                            total = float(item["total"])
                        except ValueError as e:
                            st.error(f"Erro ao converter valores para float: {e}")
                            continue  # Pula este item se houver erro de conversão
                        
                        # Adicionar o item ao cupom
                        cupom += f"{nome:3}     R${preco_unitario:>6.2f} x R${total:>6.2f}   {item.get('obs', '')}\n"
                    
                    # Gerar o rodapé do cupom
                    cupom += "+" * 35 + "\n"
                    cupom += f"Total da Venda: R${float(st.session_state.orcamento_atual['total']):>6.2f}\n"
                    
                    # Codificar o texto para URL
                    cupom_url = requests.utils.quote(cupom)
                    
                    # Abrir o WhatsApp Web com o texto do cupom
                    whatsapp_url = f"https://web.whatsapp.com/send?text={cupom_url}"
                    st.markdown(f"[Abrir WhatsApp Web]({whatsapp_url})", unsafe_allow_html=True)
                else:
                    st.error("Não há itens no orçamento para enviar por WhatsApp.")

    elif menu == "Validar Orçamento":
        st.title("Validar Orçamento")
        
        # Filtro de data
        st.subheader("Filtrar por Data")
        
        # Definir o mês atual como padrão
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)  # Primeiro dia do mês atual
        ultimo_dia_mes = (primeiro_dia_mes + pd.offsets.MonthEnd(0))  # Último dia do mês atual
        
        # Permitir que o usuário selecione outras datas
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data de Início", value=primeiro_dia_mes)
        with col2:
            data_fim = st.date_input("Data de Fim", value=ultimo_dia_mes)

        # Converter as datas para o formato datetime
        data_inicio = pd.to_datetime(data_inicio)
        data_fim = pd.to_datetime(data_fim) + pd.Timedelta(days=1)  # Incluir o dia final
        
        # Converter a coluna 'data' para datetime, se necessário
        if not pd.api.types.is_datetime64_any_dtype(st.session_state.orcamentos["data"]):
            st.session_state.orcamentos["data"] = pd.to_datetime(st.session_state.orcamentos["data"], format="%d/%m/%y %H:%M", errors="coerce")
        
        # Filtrar orçamentos pendentes no período selecionado
        orcamentos_pendentes = st.session_state.orcamentos[
            (st.session_state.orcamentos["status"] == "Pendente")  &
            (st.session_state.orcamentos["data"] >= data_inicio)  &
            (st.session_state.orcamentos["data"] < data_fim)
        ]
        
        if not orcamentos_pendentes.empty:
            st.subheader("Orçamentos Pendentes")
            for index, orcamento in orcamentos_pendentes.iterrows():
                with st.expander(f"Orçamento ID: {orcamento['orcamento_id']} - Total: R$ {orcamento['total']:.2f}"):
                    st.write(f"**Data do Orçamento:** {orcamento['data']}")
                    st.write(f"**Status:** {orcamento['status']}")
                    
                    # Exibir os itens do orçamento
                    itens_orcamento = json.loads(orcamento["produtos"])
                    st.subheader("Itens do Orçamento")
                    itens_df = pd.DataFrame(itens_orcamento)
                    st.dataframe(itens_df)
                    
                    # Criar quatro colunas para os botões
                    col1, col2, col3, col4 = st.columns(4)
                     
                    # Botão para validar o orçamento como venda
                    with col1:
                        if st.button(f"Validar Orçamento {orcamento['orcamento_id']}"):
                            # Registrar a venda sem impactar o estoque
                            nova_venda = {
                                "venda_id": len(st.session_state.vendas) + 1,
                                "data": datetime.now().strftime("%d/%m/%y %H:%M"),
                                "total": float(orcamento["total"]),
                                "produtos": orcamento["produtos"]
                            }
                            st.session_state.vendas = pd.concat([st.session_state.vendas, pd.DataFrame([nova_venda])], ignore_index=True)
                            
                            # Atualizar o status do orçamento para "Validado"
                            st.session_state.orcamentos.loc[st.session_state.orcamentos["orcamento_id"] == orcamento["orcamento_id"], "status"] = "Validado"
                            # Salvar os dados no GitHub
                            salvar_dados(vendas=st.session_state.vendas, orcamentos=st.session_state.orcamentos)
                            st.success(f"Orçamento {orcamento['orcamento_id']} validado como venda com sucesso!")
            
                    # Botão para imprimir o cupom
                    with col2:
                        if st.button(f"Imprimir Cupom {orcamento['orcamento_id']}"):
                            # Gerar o cabeçalho do cupom
                            cupom = "Cupom de Venda\n"
                            cupom += "+" * 35 + "\n"
                            cupom += f"Venda ID: {orcamento['orcamento_id']:04d}   Data/Hora: {orcamento['data']}\n"
                            cupom += "+" * 35 + "\n"
                            cupom += "Descrição:              QT:      Preço          Total       Obs\n"
                             
                            # Gerar o corpo do cupom
                            for item in itens_orcamento:
                                nome = item["nome"]
                                qtde = item["quantidade"]
                                
                                # Converter preco_unitario e total para float
                                try:
                                    preco_unitario = float(item["preco_unitario"])
                                    total = float(item["total"])
                                except ValueError as e:
                                    st.error(f"Erro ao converter valores para float: {e}")
                                    continue  # Pula este item se houver erro de conversão
                                
                                # Adicionar o item ao cupom
                                cupom += f"{nome:3}     R${preco_unitario:>6.2f} x R${total:>6.2f}   {item.get('obs', '')}\n"
                            
                            # Gerar o rodapé do cupom
                            cupom += "+" * 35 + "\n"
                            cupom += f"Total da Venda: R${float(orcamento['total']):>6.2f}\n"
                            
                            # Exibir o cupom no Streamlit
                            st.text(cupom)
                
                    # Botão para editar o orçamento
                    with col3:
                        if st.button(f"Editar Orçamento {orcamento['orcamento_id']}"):
                            st.session_state.orcamento_editavel = orcamento
                            st.session_state.orcamento_editavel["itens"] = json.loads(orcamento["produtos"])
                            st.session_state.orcamento_editavel["total"] = float(orcamento["total"])
                            st.session_state.orcamento_editavel["orcamento_id"] = orcamento["orcamento_id"]
                            st.session_state.orcamento_editavel["data"] = orcamento["data"]
                            st.session_state.orcamento_editavel["status"] = orcamento["status"]
                            st.rerun()

                    # Botão para enviar por WhatsApp
                    with col4:
                        if st.button(f"Enviar por WhatsApp {orcamento['orcamento_id']}"):
                            # Gerar o texto do cupom
                            cupom = "Cupom de Venda\n"
                            cupom += "+" * 35 + "\n"
                            cupom += f"Venda ID: {orcamento['orcamento_id']:04d}   Data/Hora: {orcamento['data']}\n"
                            cupom += "+" * 35 + "\n"
                            cupom += "Descrição:              QT:      Preço          Total       Obs\n"
                            
                            # Gerar o corpo do cupom
                            for item in itens_orcamento:
                                nome = item["nome"]
                                qtde = item["quantidade"]
                                
                                # Converter preco_unitario e total para float
                                try:
                                    preco_unitario = float(item["preco_unitario"])
                                    total = float(item["total"])
                                except ValueError as e:
                                    st.error(f"Erro ao converter valores para float: {e}")
                                    continue  # Pula este item se houver erro de conversão
                                
                                # Adicionar o item ao cupom
                                cupom += f"{nome:3}     R${preco_unitario:>6.2f} x R${total:>6.2f}   {item.get('obs', '')}\n"
                            
                            # Gerar o rodapé do cupom
                            cupom += "+" * 35 + "\n"
                            cupom += f"Total da Venda: R${float(orcamento['total']):>6.2f}\n"
                            
                            # Codificar o texto para URL
                            cupom_url = requests.utils.quote(cupom)
                            
                            # Gerar o link do WhatsApp
                            whatsapp_url = f"https://web.whatsapp.com/send?text={cupom_url}"
                            st.markdown(f"[Abrir WhatsApp Web]({whatsapp_url})", unsafe_allow_html=True)

        else:
            st.warning("Nenhum orçamento pendente encontrado no período selecionado.")

        # Seção para editar o orçamento
        if "orcamento_editavel" in st.session_state and st.session_state.orcamento_editavel is not None:
            st.title("Editar Orçamento")
            st.subheader(f"Orçamento ID: {st.session_state.orcamento_editavel['orcamento_id']}")
            st.write(f"Data: {st.session_state.orcamento_editavel['data']}")
            
            # Exibir itens atuais do orçamento
            st.subheader("Itens Atuais do Orçamento")
            itens_df = pd.DataFrame(st.session_state.orcamento_editavel["itens"])
            st.dataframe(itens_df[["nome", "quantidade", "preco_unitario", "total", "obs"]])
            # Exibir itens atuais do orçamento
            st.subheader("Itens Atuais do Orçamento")
            itens_df = pd.DataFrame(st.session_state.orcamento_editavel["itens"])
            st.dataframe(itens_df[["nome", "quantidade", "preco_unitario", "total", "obs"]])
            
            # Adicionar novos itens ao orçamento
            st.subheader("Adicionar Novos Itens ao Orçamento")
            produtos_list = st.session_state.produtos["nome"].tolist()
            produto_selecionado = st.selectbox("Selecione o Produto", produtos_list)
            
            # Obter o ID e o preço do produto selecionado
            produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
            preco_unitario = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "preco"].values[0]
            
            # Campo para informar a quantidade desejada
            quantidade = st.number_input("Quantidade", min_value=1)
            
            # Campo para o preço (editável)
            preco_orcamento = st.number_input("Preço Unitário (R$)", value=float(preco_unitario), format="%.2f")

            # Campo para observações
            obs = st.text_input("Observações")
            
            # Botão para adicionar o produto ao orçamento
            if st.button("Adicionar Produto ao Orçamento"):
                try:
                    # Converter preco_orcamento e quantidade para float
                    preco_orcamento = float(preco_orcamento)
                    quantidade = float(quantidade)
                    
                    # Calcular o total do produto
                    total_produto = preco_orcamento * quantidade
                    
                    # Adicionar o item ao orçamento
                    item = {
                        "produto_id": produto_id,
                        "nome": produto_selecionado,
                        "quantidade": quantidade,
                        "preco_unitario": preco_orcamento,  # Usar o preço do orçamento
                        "total": float(total_produto),
                        "obs": obs  # Adicionar observações
                    }
                    st.session_state.orcamento_editavel["itens"].append(item)
                    
                    # Atualizar o total do orçamento
                    st.session_state.orcamento_editavel["total"] += total_produto
                    st.success(f"{quantidade} unidades de '{produto_selecionado}' adicionadas ao orçamento.")
                except ValueError as e:
                    st.error(f"Erro ao calcular o total do produto: {e}. Verifique se os valores de preço e quantidade são números válidos.") 
        
            # Botão para salvar as alterações no orçamento
            if st.button("Salvar Alterações no Orçamento"):
                # Atualizar o orçamento na lista de orçamentos
                st.session_state.orcamentos.loc[
                    st.session_state.orcamentos["orcamento_id"] == st.session_state.orcamento_editavel["orcamento_id"],
                    ["produtos", "total"]
                ] = [json.dumps(st.session_state.orcamento_editavel["itens"]), st.session_state.orcamento_editavel["total"]]

                # Salvar os dados no GitHub
                salvar_dados(orcamentos=st.session_state.orcamentos)

                # Limpar a sessão de orçamento editável
                st.session_state.orcamento_editavel = None
                st.success("Orçamento atualizado com sucesso!")
                st.rerun()

    elif menu == "Relatório de Vendas":
        st.title("Relatório de Vendas")

        # Filtro por data
        st.subheader("Filtrar por Data")

        # Criando duas colunas
        col1, col2 = st.columns(2)

        # Adicionando os campos nas colunas
        with col1:
            data_inicio = st.date_input("Data de Início")

        with col2:
            data_fim = st.date_input("Data de Fim")

        if st.button("Gerar Relatório"):
            # Converter a coluna 'data' para datetime, se necessário
            if not pd.api.types.is_datetime64_any_dtype(st.session_state.vendas["data"]):
                st.session_state.vendas["data"] = pd.to_datetime(st.session_state.vendas["data"], format="%d/%m/%y %H:%M", errors="coerce")

            # Converter as datas de início e fim para datetime
            data_inicio = pd.to_datetime(data_inicio)
            data_fim = pd.to_datetime(data_fim) + pd.Timedelta(days=1)  # Incluir o dia final

            # Filtrar as vendas no período selecionado
            vendas_filtradas = st.session_state.vendas[
                (st.session.vendas["data"] >= data_inicio) &
                (st.session_state.vendas["data"] < data_fim)
            ]

            if not vendas_filtradas.empty:
                st.subheader("Vendas no Período")
                for index, venda in vendas_filtradas.iterrows():
                    with st.expander(f"Venda ID: {venda['venda_id']} - Total: R$ {venda['total']:.2f} - Data da Venda: {venda['data'].strftime('%d/%m/%y %H:%M')}"):
                        st.write(f"**Data da Venda:** {venda['data'].strftime('%d/%m/%y %H:%M')}")
                        st.write(f"**Total da Venda:** R$ {venda['total']:.2f}")

                        # Exibir os itens da venda
                        itens_venda = json.loads(venda["produtos"])
                        st.subheader("Itens Vendidos")
                        itens_df = pd.DataFrame(itens_venda)
                        st.dataframe(itens_df[["nome", "quantidade", "preco_unitario", "total", "obs"]])

                        # Botões para "Imprimir Cupom" e "Enviar por WhatsApp"
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"Imprimir Cupom {venda['venda_id']}"):
                                # Gerar o cupom
                                cupom = "Cupom de Venda\n"
                                cupom += "+" * 35 + "\n"
                                cupom += f"Venda ID: {venda['venda_id']:04d}   Data/Hora: {venda['data'].strftime('%d/%m/%y %H:%M')}\n"
                                cupom += "+" * 35 + "\n"
                                cupom += "Descrição:              QT:      Preço          Total       Obs\n"
                                
                                # Adicionar os itens ao cupom
                                for item in itens_venda:
                                    nome = item["nome"]
                                    qtde = item["quantidade"]
                                    preco_unitario = float(item["preco_unitario"])
                                    total = float(item["total"])
                                    obs = item.get("obs", "")
                                    cupom += f"{nome:3}     R${preco_unitario:>6.2f} x R${total:>6.2f}   {obs}\n"
                                
                                # Adicionar o total da venda
                                cupom += "+" * 35 + "\n"
                                cupom += f"Total da Venda: R${float(venda['total']):>6.2f}\n"
                                
                                # Exibir o cupom no Streamlit
                                st.text(cupom)

                        with col2:
                            if st.button(f"Enviar por WhatsApp {venda['venda_id']}"):
                                # Gerar o cupom
                                cupom = "Cupom de Venda\n"
                                cupom += "+" * 35 + "\n"
                                cupom += f"Venda ID: {venda['venda_id']:04d}   Data/Hora: {venda['data'].strftime('%d/%m/%y %H:%M')}\n"
                                cupom += "+" * 35 + "\n"
                                cupom += "Descrição:              QT:      Preço          Total       Obs\n"
                                
                                # Adicionar os itens ao cupom
                                for item in itens_venda:
                                    nome = item["nome"]
                                    qtde = item["quantidade"]
                                    preco_unitario = float(item["preco_unitario"])
                                    total = float(item["total"])
                                    obs = item.get("obs", "")
                                    cupom += f"{nome:3}     R${preco_unitario:>6.2f} x R${total:>6.2f}   {obs}\n"
                                
                                # Adicionar o total da venda
                                cupom += "+" * 35 + "\n"
                                cupom += f"Total da Venda: R${float(venda['total']):>6.2f}\n"
                                
                                # Codificar o cupom para URL
                                cupom_url = requests.utils.quote(cupom)
                                
                                # Gerar o link do WhatsApp
                                whatsapp_url = f"https://web.whatsapp.com/send?text={cupom_url}"
                                st.markdown(f"[Abrir WhatsApp Web]({whatsapp_url})", unsafe_allow_html=True)

                # Exibir o total das vendas no período
                total_vendas_periodo = vendas_filtradas["total"].sum()
                st.subheader(f"Valor Total das Vendas no Período: R$ {total_vendas_periodo:.2f}")
            else:
                st.error("Nenhuma venda encontrada no período selecionado.")

    elif menu == "Zerar Estoque":
        st.title("Zerar Estoque")

        if st.button("Zerar Estoque"):
            st.session_state.estoque["quantidade"] = 0
            salvar_dados(estoque=st.session_state.estoque)
            st.success("Estoque zerado com sucesso!")

    elif menu == "Cadastrar Usuário":
        st.title("Cadastrar Usuário")

        with st.form("cadastro_usuario"):
            nome = st.text_input("Nome")
            email = st.text_input("Email").strip().lower()
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Cadastrar")
            if submitted:
                # Verificar se o email já existe
                if email in st.session_state.usuarios["email"].values:
                    st.error("Email já cadastrado. Por favor, use outro email.")
                else:
                    # Adicionar o novo usuário ao DataFrame
                    novo_usuario = pd.DataFrame({
                        "nome": [nome],
                        "email": [email],
                        "senha": [senha]
                    })
                    st.session_state.usuarios = pd.concat([st.session_state.usuarios, novo_usuario], ignore_index=True)

                    # Salvar os dados no GitHub
                    gravar_csv_no_github("usuarios.csv", st.session_state.usuarios)
                    st.success(f"Usuário '{nome}' cadastrado com sucesso!")

        # Exibir os usuários cadastrados em um grid
        st.subheader("Usuários Cadastrados")
        if not st.session_state.usuarios.empty:
            st.dataframe(st.session_state.usuarios[["nome", "email"]])
        else:
            st.warning("Nenhum usuário cadastrado.")

    elif menu == "Logout":
        st.session_state.logado = False
        st.success("Você foi desconectado com sucesso.")
        st.rerun()
