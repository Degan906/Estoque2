import streamlit as st
import pandas as pd
import requests
import base64
import io
import json
import numpy as np
from datetime import datetime  # Importar datetime para manipulação de datas

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
    
    # Adicionar a coluna 'nome' ao estoque
    if estoque is not None and produtos is not None:
        estoque = estoque.merge(
            produtos[["id", "nome"]],
            left_on="produto_id",
            right_on="id",
            how="left"
        ).drop(columns=["id"])  # Remover a coluna 'id' duplicada
    
    # Converter a coluna 'data' para datetime ao carregar os dados
    if vendas is not None and "data" in vendas.columns:
        vendas["data"] = pd.to_datetime(vendas["data"], format="%d/%m/%y %H:%M", errors="coerce")
    
    return produtos, usuarios, estoque, vendas

# Inicializar os dados na sessão
if "produtos" not in st.session_state:
    st.session_state.produtos, st.session_state.usuarios, st.session_state.estoque, st.session_state.vendas = carregar_dados()

# Função para salvar dados de volta nos arquivos CSV no GitHub
def salvar_dados(produtos=None, estoque=None, vendas=None):
    if produtos is not None:
        gravar_csv_no_github("produtos.csv", produtos)
    if estoque is not None:
        # Garantir que a coluna 'nome' esteja presente
        if "nome" not in estoque.columns and "produto_id" in estoque.columns:
            estoque = estoque.merge(
                st.session_state.produtos[["id", "nome"]],
                left_on="produto_id",
                right_on="id",
                how="left"
            ).drop(columns=["id"])  # Remover a coluna 'id' duplicada
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
            "Registro de Vendas",
            "Relatório de Vendas",
            "Zerar Estoque",  # Nova opção no menu
            "Logout"
        ]
    )

    if menu == "Dashboard":
        st.title("Dashboard")
        st.write("Bem-vindo ao sistema de controle de estoque e vendas!")

        # Exibir a tabela de estoque
        st.subheader("Tabela de Estoque")
        if st.session_state.estoque is not None:
            try:
                # Verificar se a coluna 'quantidade' existe no DataFrame estoque
                if "quantidade" not in st.session_state.estoque.columns:
                    st.error("A coluna 'quantidade' não foi encontrada no arquivo 'estoque.csv'.")
                else:
                    # Selecionar as colunas relevantes
                    tabela_estoque = st.session_state.estoque[["produto_id", "nome", "quantidade"]]
                    
                    # Exibir a tabela
                    st.dataframe(tabela_estoque)
            except Exception as e:
                st.error(f"Erro ao processar a tabela de estoque: {str(e)}")
        else:
            st.error("Erro ao carregar o estoque. Verifique o arquivo 'estoque.csv' no repositório do GitHub.")

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

    elif menu == "Registro de Vendas":
        st.title("Registro de Vendas")
        
        # Lista de produtos disponíveis
        produtos_list = st.session_state.produtos["nome"].tolist()
        produto_selecionado = st.selectbox("Selecione o Produto", produtos_list)
        
        # Obter o ID do produto selecionado
        produto_id = st.session_state.produtos.loc[st.session_state.produtos["nome"] == produto_selecionado, "id"].values[0]
        
        # Verificar a quantidade disponível em estoque
        quantidade_estoque = st.session_state.estoque.loc[st.session_state.estoque["produto_id"] == produto_id, "quantidade"].values
        quantidade_disponivel = quantidade_estoque[0] if len(quantidade_estoque) > 0 else 0
        
        # Exibir a quantidade disponível em estoque
        st.write(f"Quantidade disponível em estoque: **{quantidade_disponivel}** unidades")
        
        quantidade = st.number_input("Quantidade", min_value=1, max_value=quantidade_disponivel if quantidade_disponivel > 0 else 1)
        
        # Obter o preço unitário do produto selecionado
        preco_unitario = st.session_state.produtos.loc[st.session_state.produtos["id"] == produto_id, "preco"].values[0]
        total_produto = quantidade * preco_unitario
        
        # Botão para adicionar o produto à lista de vendas
        if "itens_venda" not in st.session_state:
            st.session_state.itens_venda = []
        
        if st.button("Adicionar Produto à Venda"):
            if quantidade > quantidade_disponivel:
                st.error("Quantidade solicitada maior que o estoque disponível!")
            else:
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
                    "data": datetime.now().strftime("%d/%m/%y %H:%M"),  # Formato dd/MM/yy hh:mm
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
            st.session_state.vendas["data"] = pd.to_datetime(st.session_state.vendas["data"], format="%d/%m/%y %H:%M", errors="coerce")
            
            # Converter as datas de início e fim para datetime
            data_inicio = pd.to_datetime(data_inicio)
            data_fim = pd.to_datetime(data_fim) + pd.Timedelta(days=1)  # Incluir o dia final
            
            # Filtrar as vendas no intervalo de datas
            vendas_filtradas = st.session_state.vendas[
                (st.session_state.vendas["data"] >= data_inicio) & 
                (st.session_state.vendas["data"] < data_fim)  # Usar < para não incluir o dia seguinte
            ]
            
            if not vendas_filtradas.empty:
                # Exibir o grid com as vendas
                st.subheader("Vendas no Período")
                
                # Criar uma lista expansível para cada venda
                for index, venda in vendas_filtradas.iterrows():
                    with st.expander(f"Venda ID: {venda['venda_id']} - Total: R$ {venda['total']:.2f}"):
                        st.write(f"**Data da Venda:** {venda['data'].strftime('%d/%m/%y %H:%M')}")  # Formato dd/MM/yy hh:mm
                        st.write(f"**Total da Venda:** R$ {venda['total']:.2f}")
                        
                        # Exibir os itens vendidos
                        itens_venda = json.loads(venda["produtos"])
                        st.subheader("Itens Vendidos")
                        itens_df = pd.DataFrame(itens_venda)
                        st.dataframe(itens_df[["nome", "quantidade", "preco_unitario", "total"]])
                
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
