import streamlit as st
st.set_page_config(page_title="Controle de Compras", layout="wide")

def main():
    import json
    import gspread
    import pandas as pd
    from datetime import datetime
    from oauth2client.service_account import ServiceAccountCredentials
    import re

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    SHEET_NAME = "controle de compras"
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

    if "qtd_parcelas" not in st.session_state:
        st.session_state.qtd_parcelas = 1
    if "last_qtd_parcelas" not in st.session_state:
        st.session_state.last_qtd_parcelas = st.session_state.qtd_parcelas
    if "trigger_rerun" not in st.session_state:
        st.session_state.trigger_rerun = False

    st.title("📦 Controle de Compras")

    with st.expander("➕ Nova Compra", expanded=True):
        fornecedor = st.text_input("Fornecedor")
        cnpj = st.text_input("CNPJ")
        empresa_compradora = st.text_input("Empresa Compradora")
        data_pedido = st.date_input("Data do Pedido", format="DD/MM/YYYY")
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Boleto", "Transferência", "PIX", "Cartão", "Outro"])
        valor_total = st.number_input("Valor da Compra (R$)", min_value=0.0, step=0.01, format="%.2f")

        data_pagamento = None
        parcelas_info = ""
        vencimentos = []

        if forma_pagamento == "Boleto":
            st.number_input("Quantidade de Parcelas", min_value=1, max_value=12, step=1, key="qtd_parcelas")

            if st.session_state.qtd_parcelas != st.session_state.last_qtd_parcelas:
                st.session_state.last_qtd_parcelas = st.session_state.qtd_parcelas
                st.session_state.trigger_rerun = True

            st.markdown("#### 📅 Datas de Vencimento das Parcelas:")
            for i in range(st.session_state.qtd_parcelas):
                venc = st.date_input(f"Parcela {i+1} - Vencimento", key=f"venc_{i}", format="DD/MM/YYYY")
                vencimentos.append(venc)

            valor_parcela = valor_total / st.session_state.qtd_parcelas
            valor_formatado = f"R$ {valor_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            parcelas_info = f"{st.session_state.qtd_parcelas}x de {valor_formatado}\n" +                             "Vencimentos: " + ", ".join([v.strftime("%d/%m/%Y") for v in vencimentos])
            data_pagamento = vencimentos[0]
        else:
            data_pagamento = st.date_input("Data de Pagamento", format="DD/MM/YYYY")

        if st.button("Registrar Compra"):
            if not all([fornecedor, cnpj, empresa_compradora, forma_pagamento, valor_total > 0]):
                st.error("❌ Todos os campos devem ser preenchidos corretamente.")
            else:
                valor_formatado_total = f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                nova_linha = [
                    fornecedor,
                    cnpj,
                    empresa_compradora,
                    data_pedido.strftime("%d/%m/%Y"),
                    forma_pagamento,
                    valor_formatado_total if forma_pagamento != "Boleto" else parcelas_info,
                    data_pagamento.strftime("%d/%m/%Y"),
                    parcelas_info if forma_pagamento == "Boleto" else "-"
                ]
                worksheet.append_row(nova_linha)
                st.success("✅ Compra registrada com sucesso!")
                st.session_state.trigger_rerun = True

if __name__ == "__main__":
    main()
