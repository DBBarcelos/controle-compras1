import streamlit as st
import json
import gspread
import pandas as pd
from datetime import datetime
import locale
from oauth2client.service_account import ServiceAccountCredentials
import re

# === LOCALE BRASILEIRO ===
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')  # Linux (Streamlit Cloud)
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')  # Windows
    except locale.Error:
        st.warning("⚠️ Não foi possível aplicar formatação local. Moedas e datas podem aparecer com formatação padrão.")

# Carregar credenciais dos secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_NAME = "controle de compras"

# === PLANILHA GOOGLE SHEETS ===
try:
    spreadsheet = client.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    spreadsheet = client.create(SHEET_NAME)
    spreadsheet.share('', perm_type='anyone', role='writer')

worksheet = spreadsheet.sheet1
headers = [
    "Fornecedor", "CNPJ", "Empresa Compradora",
    "Data do Pedido", "Forma de Pagamento", "Valor",
    "Data de Pagamento", "Parcelas"
]
if worksheet.row_values(1) != headers:
    worksheet.clear()
    worksheet.append_row(headers)

# === SESSION STATE ===
if "qtd_parcelas" not in st.session_state:
    st.session_state.qtd_parcelas = 1
if "last_qtd_parcelas" not in st.session_state:
    st.session_state.last_qtd_parcelas = st.session_state.qtd_parcelas
if "trigger_rerun" not in st.session_state:
    st.session_state.trigger_rerun = False

# === INTERFACE PRINCIPAL ===
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("📦 Sistema de Controle de Compras")

st.subheader("Nova Compra")
fornecedor = st.text_input("Fornecedor")
cnpj = st.text_input("CNPJ")
empresa_compradora = st.text_input("Empresa Compradora")
data_pedido = st.date_input("Data do Pedido", format="DD/MM/YYYY")
forma_pagamento = st.selectbox("Forma de Pagamento", ["Boleto", "Transferência", "PIX", "Cartão", "Outro"])
valor_total = st.number_input("Valor da Compra (R$)", min_value=0.0, step=0.01, format="%.2f")

data_pagamento = None
parcelas_info = ""
vencimentos = []

# === BOLETO COM PARCELAS ===
if forma_pagamento == "Boleto":
    st.number_input(
        "Quantidade de Parcelas", min_value=1, max_value=12, step=1,
        key="qtd_parcelas"
    )

    if st.session_state.qtd_parcelas != st.session_state.last_qtd_parcelas:
        st.session_state.last_qtd_parcelas = st.session_state.qtd_parcelas
        st.session_state.trigger_rerun = True

    st.markdown("#### 📅 Datas de Vencimento das Parcelas:")
    for i in range(st.session_state.qtd_parcelas):
        venc = st.date_input(f"Parcela {i+1} - Vencimento", key=f"venc_{i}", format="DD/MM/YYYY")
        vencimentos.append(venc)

    valor_parcela = valor_total / st.session_state.qtd_parcelas
    parcelas_info = f"{st.session_state.qtd_parcelas}x de {locale.currency(valor_parcela, grouping=True)}\n"
    parcelas_info += "Vencimentos: " + ", ".join([v.strftime("%d/%m/%Y") for v in vencimentos])
    data_pagamento = vencimentos[0]
else:
    data_pagamento = st.date_input("Data de Pagamento", format="DD/MM/YYYY")

# === REGISTRAR COMPRA ===
if st.button("Registrar Compra"):
    if not all([fornecedor, cnpj, empresa_compradora, forma_pagamento, valor_total > 0]):
        st.error("❌ Todos os campos devem ser preenchidos corretamente.")
    else:
        nova_linha = [
            fornecedor,
            cnpj,
            empresa_compradora,
            data_pedido.strftime("%d/%m/%Y"),
            forma_pagamento,
            locale.currency(valor_total, grouping=True) if forma_pagamento != "Boleto" else parcelas_info,
            data_pagamento.strftime("%d/%m/%Y"),
            parcelas_info if forma_pagamento == "Boleto" else "-"
        ]
        worksheet.append_row(nova_linha)
        st.success("✅ Compra registrada com sucesso!")
        st.session_state.trigger_rerun = True

# === EXIBIÇÃO DA TABELA COM DATAS FORMATADAS ===
st.subheader("📋 Compras Registradas")
dados = worksheet.get_all_records()
df = pd.DataFrame(dados)

if not df.empty:
    df["ID"] = df.index + 2

    # Formatando colunas de data
    def formatar_data(data):
        try:
            return pd.to_datetime(data, dayfirst=True).strftime("%d/%m/%Y")
        except:
            return data

    df["Data do Pedido"] = df["Data do Pedido"].apply(formatar_data)
    df["Data de Pagamento"] = df["Data de Pagamento"].apply(formatar_data)

    # Formatando vencimentos dentro do campo Parcelas
    def formatar_vencimentos(texto):
        if isinstance(texto, str) and "Vencimentos:" in texto:
            datas = re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", texto)
            for d in datas:
                try:
                    data_formatada = pd.to_datetime(d, dayfirst=True).strftime("%d/%m/%Y")
                    texto = texto.replace(d, data_formatada)
                except:
                    pass
        return texto

    df["Parcelas"] = df["Parcelas"].apply(formatar_vencimentos)

    df = df[["ID"] + headers].astype(str)
    st.table(df)

    # Exclusão
    st.markdown("### ❌ Excluir um Cadastro")
    excluir_id = st.selectbox("Selecione o ID da compra para excluir:", df["ID"].astype(int))

    if st.button("Excluir Cadastro Selecionado"):
        worksheet.delete_rows(int(excluir_id))
        st.success(f"✅ Cadastro da linha {excluir_id} excluído com sucesso!")
        st.session_state.trigger_rerun = True
else:
    st.info("Nenhuma compra registrada ainda.")

# === RERUN SE NECESSÁRIO ===
if st.session_state.trigger_rerun:
    st.session_state.trigger_rerun = False
    st.rerun()
