import streamlit as st
import pandas as pd
import requests
import base64
import io
import json
import numpy as np

# Configuração da página
st.set_page_config(page_title="Controle de Estoque e Vendas", layout="wide")

# Configurações do GitHub
GITHUB_REPO = "https://api.github.com/repos/Degan906/Estoque2/contents"
GITHUB_TOKEN = "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"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Função para ler um arquivo CSV do GitHub
def ler_csv_do_github(nome_arquivo):
    url = f"{GITHUB_REPO}/{nome_arquivo}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        conteudo = base64.b64decode(response.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(conteudo))
    else:
        st.error(f"Erro ao ler {nome_arquivo} do GitHub: {response.text}")
        return None

# Função para gravar um arquivo CSV no GitHub
def gravar_csv_no_github(nome_arquivo, df):
    url = f"{GITHUB_REPO}/{nome_arquivo}"
    
    # Ler o arquivo atual para obter o SHA
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        conteudo_atual = response.json()
        sha = conteudo_atual["sha"]  # Obter o SHA do conteúdo atual
    else:
        st.error(f"Erro ao ler {nome_arquivo} do GitHub: {response.text}")
        return
    
    # Preparar o novo conteúdo
    conteudo = df.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo.encode("utf-8")).decode("utf-8")
    data = {
        "message": f"Atualizando {nome_arquivo}",
        "content": conteudo_base64,
        "sha": sha  # Incluir o SHA do conteúdo atual
    }
    
    # Enviar a requisição PUT para atualizar o arquivo
    response = requests.put(url, headers=HEADERS, json=data)
    if response.status_code not in [200, 201]:
        st.error(f"Erro ao gravar {nome_arquivo} no GitHub: {response.text}")
    else:
        st.success(f"{nome_arquivo} atualizado com sucesso!")

# Função para carregar dados dos arquivos CSV do GitHub
def carregar_dados():
    produtos = ler_csv_do_github("produtos.csv")
    usuarios = ler_csv_do_github("usuarios.csv")
    estoque = ler_csv_do_github("estoque.csv")
    vendas = ler_csv_do_github("vendas.csv")
    return produtos, usuarios, estoque, vendas

# Inicializar os dados na sessão
if "produtos" not in st.session_state:
    st.session_state.produtos, st.session_state.usuarios, st.session_state.estoque, st.session_state.vendas = carregar_dados()

# Função para salvar dados de volta nos arquivos CSV no GitHub
def salvar_dados(produtos=None, estoque=None, vendas=None):
    if produtos is not None:
        gravar_csv_no_github("produtos.csv", produtos)
    if estoque is not None:
        gravar_csv_no_github("estoque.csv", estoque)
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
    email = st.text_input("Email").strip().lower()  # Remover espaços e converter para minúsculas
    senha = st.text_input("Senha", type="password").strip()  # Remover espaços
    if st.button("Entrar"):
        # Converter a coluna 'senha' para string para evitar problemas de tipo
        st.session_state.usuarios["senha"] = st.session_state.usuarios["senha"].astype(str)
        
        # Filtrar o usuário com base no email e senha
        usuario = st.session_state.usuarios[
            (st.session_state.usuarios["email"].str.strip().str.lower() == email) & 
            (st.session_state.usuarios["senha"].str.strip() == senha)
        ]
        if not usuario.empty:
            st.session_state.logado = True
            st.success("Login realizado com sucesso!")
        else:
            st.error("Email ou senha inválidos.")

# Sistema Principal (apenas acessível após login)
else:
    # Adicionar um botão de atualização no menu lateral
    if st.sidebar.button("Atualizar Dados"):
        st.session_state.produtos, st.session_state.usuarios, st.session_state.estoque, st.session_state.vendas = carregar_dados()
        st.success("Dados atualizados com sucesso!")

    # Menu lateral
    menu = st.sidebar.selectbox(
        "Menu",
        [
            "Dashboard",
            "Cadastro de Produtos",
            "Entrada no Estoque",
            "Controle de Estoque",
            "Registro de Vendas",
            "Relatório de Vendas",
            "Zerar Estoque",  # Nova opção no menu
            "Logout"
        ]
    )

    if menu == "Dashboard":
        st.title("Dashboard")
        st.write("Bem-vindo ao sistema de controle de estoque e vendas!")

    elif menu == "Cadastro de Produtos":
        st.title("Cadastro de Produtos")
        with st.form("cadastro_produto"):
            nome = st.text_input("Nome do Produto")
            preco = st.number_input("Preço", min_value=0.0, format="%.2f")
            submitted = st.form_submit_button("Cadastrar")
            if submitted:
                novo_id = st.session_state.produtos["id"].max() + 1 if not st.session_state.produtos.empty else 1
                novo_produto = pd.DataFrame({"id": [novo_id], "nome": [nome], "preco": [preco], "quantidade": [0]})
                st.session_state.produtos = pd.concat([st.session_state.produtos, novo_produto], ignore_index=True)
                salvar_dados(produtos=st.session_state.produtos)
                st.success(f"Produto '{nome}' cadastrado com sucesso!")

    elif menu == "Entrada no Estoque":
        st.title("Entrada no Estoque")
        produtos_list = st.session_state.produtos["nome"].tolist()
        produto_selecionado = st.selectbox("Selecione o Produto", produtos_list)
        quantidade = st.number_input("Quantidade", min_value=1)
        if st.button("Registrar Entrada"):
            produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
            estoque_atual = st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id, "quantidade"]
            if not estoque_atual.empty:
                st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id, "quantidade"] += quantidade
            else:
                novo_estoque = pd.DataFrame({"produto_id": [produto_id], "quantidade": [quantidade]})
                st.session_state.estoque = pd.concat([st.session_state.estoque, novo_estoque], ignore_index=True)
            salvar_dados(estoque=st.session_state.estoque)
            st.success(f"{quantidade} unidades de '{produto_selecionado}' adicionadas ao estoque.")

    elif menu == "Controle de Estoque":
        st.title("Controle de Estoque")
        
        # Verificar se as colunas necessárias existem nos DataFrames
        if "produto_id" not in st.session_state.estoque.columns or "id" not in st.session_state.produtos.columns:
            st.error("As colunas 'produto_id' (estoque) ou 'id' (produtos) não foram encontradas.")
        else:
            # Fazer o merge entre estoque e produtos
            try:
                # Depuração: Exibir os DataFrames antes do merge
                st.write("DataFrame 'estoque':", st.session_state.estoque)
                st.write("DataFrame 'produtos':", st.session_state.produtos)
                
                # Realizar o merge
                estoque_com_nomes = st.session_state.estoque.merge(
                    st.session_state.produtos, 
                    left_on="produto_id", 
                    right_on="id", 
                    how="left"
                )
                
                # Depuração: Exibir o DataFrame após o merge
                st.write("DataFrame após o merge:", estoque_com_nomes)
                
                # Verificar se a coluna 'quantidade' existe após o merge
                if "quantidade" not in estoque_com_nomes.columns:
                    st.error("A coluna 'quantidade' não foi encontrada após o merge. Verifique o arquivo 'estoque.csv'.")
                else:
                    # Certificar-se de que a coluna 'quantidade' é numérica
                    estoque_com_nomes["quantidade"] = pd.to_numeric(estoque_com_nomes["quantidade"], errors="coerce")
                    
                    # Filtrar apenas as colunas relevantes
                    tabela_estoque = estoque_com_nomes[["nome", "quantidade"]]
                    
                    # Exibir a tabela
                    st.subheader("Estoque Atual")
                    st.dataframe(tabela_estoque)
                    
                    # Botão para zerar o estoque
                    if st.button("Zerar Estoque"):
                        st.session_state.estoque["quantidade"] = 0  # Zerar a quantidade de todos os produtos
                        salvar_dados(estoque=st.session_state.estoque)  # Salvar a alteração no GitHub
                        st.success("Estoque zerado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao processar os dados de estoque: {e}")

    elif menu == "Registro de Vendas":
        st.title("Registro de Vendas")
        
        # Lista de produtos disponíveis
        produtos_list = st.session_state.produtos["nome"].tolist()
        produto_selecionado = st.selectbox("Selecione o Produto", produtos_list)
        quantidade = st.number_input("Quantidade", min_value=1)
        
        # Obter o preço unitário do produto selecionado
        produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
        preco_unitario = st.session_state.produtos.loc[st.session_state.produtos["id"] == produto_id, "preco"].values[0]
        total_produto = quantidade * preco_unitario
        
        # Botão para adicionar o produto à lista de vendas
        if "itens_venda" not in st.session_state:
            st.session_state.itens_venda = []
        
        if st.button("Adicionar Produto à Venda"):
            item = {
                "produto_id": produto_id,
                "nome": produto_selecionado,
                "quantidade": quantidade,
                "preco_unitario": preco_unitario,
                "total": total_produto
            }
            st.session_state.itens_venda.append(item)
            st.success(f"{quantidade} unidades de '{produto_selecionado}' adicionadas à venda.")
        
        # Exibir os itens adicionados à venda
        if st.session_state.itens_venda:
            st.subheader("Itens na Venda Atual")
            itens_df = pd.DataFrame(st.session_state.itens_venda)
            st.dataframe(itens_df)
            
            # Calcular o total da venda
            total_venda = itens_df["total"].sum()
            st.subheader(f"Total da Venda: R$ {total_venda:.2f}")
        
        # Finalizar a venda
        if st.button("Finalizar Venda"):
            if st.session_state.itens_venda:
                # Atualizar o estoque
                for item in st.session_state.itens_venda:
                    produto_id = item["produto_id"]
                    quantidade = item["quantidade"]
                    st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id, "quantidade"] -= quantidade
                
                # Salvar a venda no arquivo CSV
                nova_venda = {
                    "venda_id": len(st.session_state.vendas) + 1,
                    "data": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    "total": float(total_venda),  # Converter para float
                    "produtos": json.dumps(converter_para_json_serializavel(st.session_state.itens_venda))  # Usar função auxiliar
                }
                st.session_state.vendas = pd.concat([st.session_state.vendas, pd.DataFrame([nova_venda])], ignore_index=True)
                
                # Chamar a função para salvar os dados
                salvar_dados(estoque=st.session_state.estoque, vendas=st.session_state.vendas)
                
                # Limpar a sessão de venda
                st.session_state.itens_venda = []
                st.success("Venda finalizada com sucesso!")
            else:
                st.error("Não há itens na venda para finalizar.")

    elif menu == "Relatório de Vendas":
        st.title("Relatório de Vendas")
        
        # Filtro por data
        st.subheader("Filtrar por Data")
        data_inicio = st.date_input("Data de Início")
        data_fim = st.date_input("Data de Fim")
        
        if st.button("Gerar Relatório"):
            # Certificar-se de que a coluna 'data' é do tipo datetime
            st.session_state.vendas["data"] = pd.to_datetime(st.session_state.vendas["data"], format="%Y-%m-%d", errors="coerce")
            
            # Filtrar as vendas no intervalo de datas
            vendas_filtradas = st.session_state.vendas[
                (st.session_state.vendas["data"] >= pd.Timestamp(data_inicio)) & 
                (st.session_state.vendas["data"] <= pd.Timestamp(data_fim))
            ]
            
            if not vendas_filtradas.empty:
                # Exibir o grid com as vendas
                st.subheader("Vendas no Período")
                st.dataframe(vendas_filtradas[["venda_id", "data", "total"]])
                
                # Calcular o valor total das vendas no período
                total_vendas_periodo = vendas_filtradas["total"].sum()
                st.subheader(f"Valor Total das Vendas no Período: R$ {total_vendas_periodo:.2f}")
            else:
                st.error("Nenhuma venda encontrada no período selecionado.")

    elif menu == "Zerar Estoque":
        st.title("Zerar Estoque")
        
        # Confirmação para zerar o estoque
        if st.button("Zerar Estoque"):
            st.session_state.estoque["quantidade"] = 0  # Zerar a quantidade de todos os produtos
            salvar_dados(estoque=st.session_state.estoque)  # Salvar a alteração no GitHub
            st.success("Estoque zerado com sucesso!")

    elif menu == "Logout":
        st.session_state.logado = False
        st.success("Você foi desconectado com sucesso.")
        st.rerun()
